"""实时数据服务 — 只拉取已入池股票，存入 realtime_cache 临时库。"""
from __future__ import annotations

import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


def get_pool_codes(conn) -> list[str]:
    """获取所有用户策略池中的股票代码（去重）。"""
    rows = conn.execute(
        "SELECT DISTINCT code FROM stock_pool WHERE status='in'"
    ).fetchall()
    return [r["code"] for r in rows]


def detect_market(code: str) -> str:
    """根据代码判断市场分类。"""
    symbol = code.split(".")[0]
    if symbol.startswith("688"):
        return "科创板"
    if symbol.startswith("3"):
        return "创业板"
    if symbol.startswith("6"):
        return "沪市主板"
    if symbol.startswith("0") or symbol.startswith("2"):
        return "深市主板"
    if symbol.startswith("8") or symbol.startswith("4"):
        return "北交所"
    return "其他"


def pull_realtime_for_pool(conn) -> int:
    """拉取所有入池股票的实时行情（新浪财经），写入 realtime_cache。"""
    from src.stock.services.sina_client import AKShareClient

    codes = get_pool_codes(conn)
    if not codes:
        return 0

    try:
        client = AKShareClient()
        rt_map = client.get_realtime_batch(codes)  # {code: {latest,change_ratio,...}}
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updated = 0

        for code, rt in rt_map.items():
            conn.execute("""
                INSERT OR REPLACE INTO realtime_cache
                (code, name, price, change_pct, open_price, high, low, pre_close,
                 volume, amount, market, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                code, rt.get("name", ""),
                rt.get("latest") or rt.get("price", 0),
                rt.get("change_ratio") or rt.get("change_pct", 0),
                rt.get("open", 0), rt.get("high", 0), rt.get("low", 0),
                rt.get("settlement") or rt.get("pre_close", 0),
                rt.get("volume", 0), rt.get("amount", 0),
                detect_market(code), now_str
            ))
            updated += 1

        conn.commit()
        logger.info("实时数据更新（新浪）%d 只", updated)
        return updated

    except Exception as e:
        logger.warning("pull_realtime_for_pool failed: %s", e)
        return 0


def clear_realtime_cache(conn) -> None:
    """清空实时数据缓存（每天6:00调用）。"""
    conn.execute("DELETE FROM realtime_cache")
    conn.commit()
    logger.info("实时数据缓存已清空")


def get_from_cache(conn, code: str) -> dict | None:
    """从缓存读取单只股票实时数据。"""
    row = conn.execute(
        "SELECT * FROM realtime_cache WHERE code=?", (code,)
    ).fetchone()
    if not row:
        return None
    return {
        "code": row["code"],
        "name": row["name"],
        "price": row["price"],
        "change_pct": row["change_pct"],
        "open": row["open_price"],
        "high": row["high"],
        "low": row["low"],
        "pre_close": row["pre_close"],
        "volume": row["volume"],
        "amount": row["amount"],
        "market": row["market"],
        "updated_at": row["updated_at"],
    }


def is_pull_time() -> bool:
    """判断当前是否在拉取时段（8:30-15:05，周一至周五）。"""
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    t = now.hour * 100 + now.minute
    return 830 <= t <= 1505
