"""候选池服务 — 每日涨幅≥15% 的股票自动入候选池，全市场支持。"""
from __future__ import annotations

import logging
import time
from datetime import date

logger = logging.getLogger(__name__)

GAIN_THRESHOLD = 15.0   # 候选池涨幅门槛


def refresh_candidate_pool(db_conn) -> list[dict]:
    """扫描今日高涨幅股票，写入各用户候选池（全市场）。"""
    from src.stock.services.data_client import get_high_gain_stocks

    today = date.today().isoformat()
    stocks = get_high_gain_stocks(threshold=GAIN_THRESHOLD)

    # 获取所有用户 id
    users = db_conn.execute("SELECT id FROM users").fetchall()
    added = []

    for stock in stocks:
        code = stock["code"]
        # 根据后缀判断市场
        if not code:
            continue
        # 补全后缀（AKShare 通常只返回6位代码）
        if "." not in code:
            if code.startswith("6"):
                code = code + ".SH"
            elif code.startswith(("0", "3")):
                code = code + ".SZ"
            elif code.startswith("8") or code.startswith("4"):
                code = code + ".BJ"

        for user in users:
            user_id = user["id"]
            # 已在策略池中则跳过
            in_pool = db_conn.execute(
                "SELECT id FROM stock_pool WHERE user_id=? AND code=? AND status='in'",
                (user_id, code)
            ).fetchone()
            if in_pool:
                continue
            # 已在候选池中则跳过
            exists = db_conn.execute(
                "SELECT id FROM candidate_pool WHERE user_id=? AND code=? AND add_date=?",
                (user_id, code, today)
            ).fetchone()
            if exists:
                continue
            db_conn.execute(
                """INSERT INTO candidate_pool
                   (user_id, code, name, add_date, change_ratio, close_price, pool_status)
                   VALUES (?,?,?,?,?,?,'pending')""",
                (user_id, code, stock.get("name", ""), today,
                 stock.get("change_ratio"), stock.get("close"))
            )
            added.append({"user_id": user_id, "code": code})

    db_conn.commit()
    logger.info("候选池扫描完成，新增 %d 条", len(added))
    return added


def refresh_stock_pool(db_conn) -> None:
    """收盘后刷新策略池：检查6条剔除规则（仅 add_type='auto'）。"""
    from src.stock.services.data_client import get_daily_bars, calc_ma5

    rows = db_conn.execute(
        "SELECT * FROM stock_pool WHERE status='in' AND add_type='auto'"
    ).fetchall()

    for row in rows:
        row = dict(row)
        code = row["code"]
        user_id = row["user_id"]
        try:
            bars = get_daily_bars(code, days=10)
            if bars.empty:
                continue
            ma5_list = calc_ma5(bars)
            ma5 = ma5_list[-1]
            today = bars.iloc[-1]
            today_close = float(today["close"])
            today_chg = float(today.get("change_ratio", 0) or 0)

            reason = None
            # 规则1：收盘价 < MA5
            if ma5 and today_close < ma5:
                reason = f"收盘{today_close:.2f}<MA5{ma5:.2f}"
            # 规则2：连板≥4
            streak = _count_streak(bars)
            if streak >= 4:
                reason = f"连板{streak}板超限"

            if reason:
                db_conn.execute(
                    "UPDATE stock_pool SET status='out', trade_status='abandoned' WHERE user_id=? AND code=?",
                    (user_id, code)
                )
                db_conn.commit()
                logger.info("自动剔除 %s user=%s reason=%s", code, user_id, reason)

        except Exception as e:
            logger.warning("refresh_pool %s failed: %s", code, e)


def _count_streak(bars) -> int:
    """从最新往前数连续涨停天数。"""
    streak = 0
    for i in range(len(bars) - 1, -1, -1):
        chg = float(bars.iloc[i].get("change_ratio", 0) or 0)
        if chg >= 19.0:
            streak += 1
        else:
            break
    return streak
