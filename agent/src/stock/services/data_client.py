"""AKShare 数据客户端 — 统一封装行情获取。"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def get_daily_bars(code: str, days: int = 30) -> pd.DataFrame:
    """获取日线 OHLCV，返回 DataFrame，含 change_ratio 列。"""
    import akshare as ak
    symbol = code.split(".")[0]
    end = date.today().strftime("%Y%m%d")
    start = (date.today() - timedelta(days=days * 2)).strftime("%Y%m%d")
    try:
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily",
                                start_date=start, end_date=end, adjust="qfq")
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.rename(columns={
            "日期": "date", "开盘": "open", "最高": "high",
            "最低": "low", "收盘": "close", "成交量": "volume",
            "涨跌幅": "change_ratio",
        })
        df["date"] = pd.to_datetime(df["date"]).dt.date
        return df.tail(days).reset_index(drop=True)
    except Exception as e:
        logger.warning("get_daily_bars %s failed: %s", code, e)
        return pd.DataFrame()


def get_realtime_price(code: str) -> Optional[dict]:
    """获取单只股票实时行情。"""
    import akshare as ak
    symbol = code.split(".")[0]
    try:
        df = ak.stock_zh_a_spot_em()
        row = df[df["代码"] == symbol]
        if row.empty:
            return None
        r = row.iloc[0]
        return {
            "code": code,
            "price": float(r.get("最新价", 0) or 0),
            "change_pct": float(r.get("涨跌幅", 0) or 0),
            "open": float(r.get("今开", 0) or 0),
            "high": float(r.get("最高", 0) or 0),
            "low": float(r.get("最低", 0) or 0),
            "pre_close": float(r.get("昨收", 0) or 0),
            "volume": float(r.get("成交量", 0) or 0),
        }
    except Exception as e:
        logger.warning("get_realtime_price %s failed: %s", code, e)
        return None


def get_gem_limit_up(trade_date: str) -> list[dict]:
    """获取指定日期创业板涨停股票列表（涨幅≥19%）。"""
    import akshare as ak
    try:
        df = ak.stock_zt_pool_em(date=trade_date)
        if df is None or df.empty:
            return []
        df = df.rename(columns={"代码": "code", "名称": "name", "涨跌幅": "change_ratio",
                                  "收盘价": "close", "开盘价": "open"})
        # 只要创业板（300开头）
        df = df[df["code"].str.startswith("3")]
        return df[["code", "name", "change_ratio", "close"]].to_dict("records")
    except Exception as e:
        logger.warning("get_gem_limit_up %s failed: %s", trade_date, e)
        return []


def get_high_gain_stocks(threshold: float = 15.0) -> list[dict]:
    """获取今日涨幅≥threshold% 的创业板股票（候选池用）。"""
    import akshare as ak
    try:
        df = ak.stock_zh_a_spot_em()
        if df is None or df.empty:
            return []
        df = df.rename(columns={"代码": "code", "名称": "name",
                                  "涨跌幅": "change_ratio", "最新价": "close"})
        df["change_ratio"] = pd.to_numeric(df["change_ratio"], errors="coerce")
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        # 创业板 + 涨幅达标
        mask = df["code"].str.startswith("3") & (df["change_ratio"] >= threshold)
        return df[mask][["code", "name", "change_ratio", "close"]].to_dict("records")
    except Exception as e:
        logger.warning("get_high_gain_stocks failed: %s", e)
        return []


def calc_ma5(bars: pd.DataFrame) -> list[Optional[float]]:
    """计算 MA5，不足5条返回 None。"""
    closes = bars["close"].tolist()
    result = []
    for i in range(len(closes)):
        if i < 4:
            result.append(None)
        else:
            result.append(round(sum(closes[i - 4:i + 1]) / 5, 2))
    return result


def is_market_open() -> bool:
    """判断当前是否在交易时段。"""
    from datetime import datetime
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    t = now.hour * 100 + now.minute
    return (925 <= t <= 1130) or (1300 <= t <= 1500)
