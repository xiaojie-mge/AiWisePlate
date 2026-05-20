"""断板识别服务 — 前日涨停今日未涨停即为断板。"""
from __future__ import annotations

import logging
import time
from datetime import date

logger = logging.getLogger(__name__)

LIMIT_UP_THRESHOLD = 19.0   # 涨幅≥19%视为涨停
MONITOR_DAYS = 3            # 断板后监控天数


def detect_break_boards(db_conn) -> list[dict]:
    """扫描所有用户策略池，识别今日断板并写库。

    Returns: 新增的断板记录列表
    """
    from src.stock.services.data_client import get_daily_bars
    results = []

    # 获取所有活跃策略池股票（去重）
    rows = db_conn.execute(
        "SELECT DISTINCT user_id, code FROM stock_pool WHERE status='in'"
    ).fetchall()

    today_str = date.today().isoformat()

    for row in rows:
        user_id, code = row["user_id"], row["code"]
        try:
            bars = get_daily_bars(code, days=10)
            if len(bars) < 2:
                continue

            prev = bars.iloc[-2]
            today = bars.iloc[-1]

            prev_chg = float(prev.get("change_ratio", 0) or 0)
            today_chg = float(today.get("change_ratio", 0) or 0)

            # 前日涨停，今日未涨停
            if prev_chg < LIMIT_UP_THRESHOLD:
                continue
            if today_chg >= LIMIT_UP_THRESHOLD:
                continue

            # 已存在今日断板记录则跳过
            exists = db_conn.execute(
                "SELECT id FROM break_board WHERE user_id=? AND code=? AND break_date=?",
                (user_id, code, today_str)
            ).fetchone()
            if exists:
                continue

            # 过滤规则：断板日最高价低于前日收盘价 → 移出策略池
            prev_close = float(prev["close"])
            today_high = float(today["high"])
            today_close = float(today["close"])
            median = (float(prev["open"]) + prev_close) / 2

            if today_high < prev_close:
                _remove_from_pool(db_conn, user_id, code, "断板日最高价低于前日收盘价")
                continue

            if today_close < median:
                _remove_from_pool(db_conn, user_id, code, "断板日收盘低于涨停板中位值")
                continue

            # 写入断板记录
            monitor_end = _add_trading_days(date.today(), MONITOR_DAYS).isoformat()
            db_conn.execute(
                """INSERT OR IGNORE INTO break_board
                   (user_id, code, break_date, prev_limit_price, median_price, monitor_end_date)
                   VALUES (?,?,?,?,?,?)""",
                (user_id, code, today_str, prev_close, round(median, 2), monitor_end)
            )
            db_conn.commit()
            results.append({"user_id": user_id, "code": code,
                             "break_date": today_str, "monitor_end": monitor_end})
            logger.info("断板记录 %s user=%s", code, user_id)

        except Exception as e:
            logger.warning("break_board scan %s failed: %s", code, e)

    return results


def _remove_from_pool(db_conn, user_id: int, code: str, reason: str) -> None:
    db_conn.execute(
        "UPDATE stock_pool SET status='out', trade_status='abandoned' WHERE user_id=? AND code=?",
        (user_id, code)
    )
    db_conn.commit()
    logger.info("移出策略池 %s user=%s reason=%s", code, user_id, reason)


def _add_trading_days(start: date, n: int) -> date:
    """简单估算：加 n 个交易日（不精确，周末跳过）。"""
    d = start
    added = 0
    while added < n:
        d = date.fromordinal(d.toordinal() + 1)
        if d.weekday() < 5:
            added += 1
    return d


def get_active_breaks(db_conn, user_id: int) -> list[dict]:
    """获取当前处于监控窗口内的断板记录。"""
    today = date.today().isoformat()
    rows = db_conn.execute(
        """SELECT bb.*, sp.name FROM break_board bb
           LEFT JOIN stock_pool sp ON bb.user_id=sp.user_id AND bb.code=sp.code
           WHERE bb.user_id=? AND bb.monitor_end_date>=?
           ORDER BY bb.break_date DESC""",
        (user_id, today)
    ).fetchall()
    return [dict(r) for r in rows]
