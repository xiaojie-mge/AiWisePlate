"""买点监控 — MA5×1.025 回踩触发。支持全市场。"""
from __future__ import annotations

import logging
from datetime import date

logger = logging.getLogger(__name__)

MA5_BUFFER = 1.025          # 买点触发缓冲区（MA5×1.025）
OPEN_MIN_PCT = -3.0         # 开盘有效最低涨跌幅


def check_buy_signals(db_conn) -> list[dict]:
    """盘中轮询：扫描断板监控窗口内的股票，判断买点是否触发。"""
    from src.stock.services.data_client import get_daily_bars, get_realtime_price, calc_ma5

    today = date.today().isoformat()
    triggered = []

    # 取所有在监控窗口内的断板记录
    rows = db_conn.execute(
        "SELECT DISTINCT user_id, code FROM break_board WHERE monitor_end_date>=?",
        (today,)
    ).fetchall()

    for row in rows:
        user_id, code = row["user_id"], row["code"]
        try:
            # 今日是否已有信号
            exists = db_conn.execute(
                "SELECT id FROM buy_signal WHERE user_id=? AND code=? AND signal_date=?",
                (user_id, code, today)
            ).fetchone()
            if exists:
                continue

            # 历史日线（计算 MA5）
            bars = get_daily_bars(code, days=10)
            if len(bars) < 5:
                continue

            ma5_list = calc_ma5(bars)
            ma5 = ma5_list[-1]
            if ma5 is None:
                continue

            prev_close = float(bars.iloc[-1]["close"])
            trigger_price = round(ma5 * MA5_BUFFER, 2)

            # 实时数据
            rt = get_realtime_price(code)
            if not rt:
                continue

            today_open = rt["open"]
            today_low = rt["low"]

            # 条件1：开盘涨跌幅 ≥ -3%
            if prev_close > 0:
                open_chg = (today_open - prev_close) / prev_close * 100
            else:
                continue
            if open_chg < OPEN_MIN_PCT:
                continue

            # 条件2：当日最低价 ≤ MA5×1.025
            if today_low > trigger_price:
                continue

            # 触发买点
            db_conn.execute(
                """INSERT OR IGNORE INTO buy_signal
                   (user_id, code, signal_date, trigger_price, ma5, is_notified)
                   VALUES (?,?,?,?,?,0)""",
                (user_id, code, today, trigger_price, ma5)
            )
            db_conn.commit()
            triggered.append({"user_id": user_id, "code": code,
                               "trigger_price": trigger_price, "ma5": ma5})
            logger.info("买点触发 %s user=%s trigger=%.2f ma5=%.2f",
                        code, user_id, trigger_price, ma5)

        except Exception as e:
            logger.warning("buy_signal check %s failed: %s", code, e)

    return triggered
