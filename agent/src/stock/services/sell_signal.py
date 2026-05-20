"""卖点监控 — 4条规则实时检查持仓。支持全市场。"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

PROFIT_TAKE_PCT = 25.0      # 止盈阈值
STOP_LOSS_PCT   = 6.0       # 止损阈值
LIMIT_UP_RATIO  = 0.195     # 接近涨停阈值（19.5%）


def check_sell_signals(db_conn) -> list[dict]:
    """盘中轮询：扫描开仓持仓，返回触发卖点的列表。"""
    from src.stock.services.data_client import get_daily_bars, get_realtime_price, calc_ma5

    positions = db_conn.execute(
        "SELECT * FROM position WHERE status='open'"
    ).fetchall()

    alerts = []
    for pos in positions:
        pos = dict(pos)
        code = pos["code"]
        buy_price = float(pos["buy_price"])
        try:
            rt = get_realtime_price(code)
            if not rt:
                continue
            latest = rt["price"]
            pre_close = rt["pre_close"]
            pnl_pct = (latest - buy_price) / buy_price * 100

            bars = get_daily_bars(code, days=10)
            ma5 = calc_ma5(bars)[-1] if len(bars) >= 5 else None

            action, reason = None, None

            # 规则1：接近涨停 → 卖半仓
            if pre_close and (latest / pre_close - 1) >= LIMIT_UP_RATIO:
                action = "SELL_HALF"
                reason = f"涨幅{(latest/pre_close-1)*100:.1f}%接近涨停，建议卖半仓"

            # 规则2：跌破MA5 → 清仓
            elif ma5 and latest < ma5:
                action = "SELL_ALL"
                reason = f"现价{latest:.2f}跌破MA5({ma5:.2f})"

            # 规则3：浮盈≥25% → 清仓
            elif pnl_pct >= PROFIT_TAKE_PCT:
                action = "SELL_ALL"
                reason = f"浮盈{pnl_pct:.1f}%，触发止盈25%"

            # 规则4：浮亏≥6% → 清仓
            elif pnl_pct <= -STOP_LOSS_PCT:
                action = "SELL_ALL"
                reason = f"浮亏{abs(pnl_pct):.1f}%，触发止损6%"

            if action:
                alerts.append({
                    "position_id": pos["id"],
                    "user_id": pos["user_id"],
                    "code": code,
                    "name": pos.get("name", ""),
                    "action": action,
                    "reason": reason,
                    "latest": latest,
                    "pnl_pct": round(pnl_pct, 2),
                })
                logger.info("卖点提醒 %s action=%s reason=%s", code, action, reason)

        except Exception as e:
            logger.warning("sell_signal check %s failed: %s", code, e)

    return alerts


def get_sell_alerts(db_conn, user_id: int) -> list[dict]:
    """API 用：返回该用户当前所有持仓的卖点状态。"""
    from src.stock.services.data_client import get_realtime_price, get_daily_bars, calc_ma5

    positions = db_conn.execute(
        "SELECT * FROM position WHERE user_id=? AND status='open'", (user_id,)
    ).fetchall()

    result = []
    for pos in positions:
        pos = dict(pos)
        code = pos["code"]
        buy_price = float(pos["buy_price"])
        rt = get_realtime_price(code)
        if not rt:
            result.append({**pos, "latest": None, "pnl_pct": None, "sell_reason": None})
            continue
        latest = rt["price"]
        pnl_pct = round((latest - buy_price) / buy_price * 100, 2) if buy_price else 0
        bars = get_daily_bars(code, days=10)
        ma5 = calc_ma5(bars)[-1] if len(bars) >= 5 else None
        pre_close = rt.get("pre_close", 0)

        reason = None
        if pre_close and (latest / pre_close - 1) >= LIMIT_UP_RATIO:
            reason = f"接近涨停，建议卖半仓"
        elif ma5 and latest < ma5:
            reason = f"跌破MA5({ma5:.2f})"
        elif pnl_pct >= PROFIT_TAKE_PCT:
            reason = f"浮盈{pnl_pct:.1f}%止盈"
        elif pnl_pct <= -STOP_LOSS_PCT:
            reason = f"浮亏{abs(pnl_pct):.1f}%止损"

        result.append({**pos, "latest": latest, "pnl_pct": pnl_pct,
                       "ma5": ma5, "sell_reason": reason})
    return result
