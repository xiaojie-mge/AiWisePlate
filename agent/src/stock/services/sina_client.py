"""
AKShare 数据客户端（新浪财经数据源）

东方财富（_em 后缀接口）在部分网络环境下不可访问，
本文件全部使用新浪财经接口作为替代。

接口对应关系：
  历史日线  stock_zh_a_daily   (新浪)  替代 stock_zh_a_hist (东方财富)
  实时行情  stock_zh_a_spot    (新浪)  替代 stock_zh_a_spot_em
  涨停板    stock_zt_pool_em           保留（若网络不通则返回空列表）
"""

import logging
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_GEM_PREFIXES = ("300", "301")


def _to_ak(code: str) -> str:
    """300750.SZ → 300750"""
    return code.split(".")[0]


def _to_sina(code: str) -> str:
    """300750.SZ → sz300750 | 600000.SH → sh600000"""
    code6 = _to_ak(code)
    if code.upper().endswith(".SH") or code6.startswith(("6", "5", "9")):
        return "sh" + code6
    return "sz" + code6


def _float(val: Any) -> float | None:
    try:
        f = float(val)
        return None if f != f else f  # NaN check
    except (TypeError, ValueError):
        return None


class AKShareClient:

    # ── 今日涨停创业板（东方财富，网络不通时返回空）────────────────

    def normalize_code(self, code: str) -> str:
        """统一代码格式：300720 → 300720.SZ，已有后缀的不变"""
        code = code.strip().upper()
        if "." in code:
            return code
        # 创业板/中小板/沪A
        if code.startswith(("300", "301", "002", "000", "003")):
            return code + ".SZ"
        if code.startswith(("600", "601", "603", "605", "688", "689")):
            return code + ".SH"
        return code + ".SZ"  # 默认深市

    def get_candidate_stocks(self, threshold: float = 15.0) -> list[dict[str, Any]]:
        """
        获取今日涨幅≥threshold%的创业板股票（候选池来源）。
        threshold 默认15%，比涨停门槛19%更宽松，覆盖强势股。
        """
        import akshare as ak
        try:
            df = ak.stock_zh_a_spot()
            # 列顺序：[0]=symbol [1]=name [2]=trade [4]=changepercent
            gem_strong = df[
                df.iloc[:, 0].str.startswith("sz3") &
                (df.iloc[:, 4] >= threshold)
            ]
            result = []
            for _, row in gem_strong.iterrows():
                sym   = str(row.iloc[0])          # sz300715
                code6 = sym[2:]                   # 300715
                result.append({
                    "code":         f"{code6}.SZ",
                    "name":         str(row.iloc[1]),
                    "change_ratio": _float(row.iloc[4]),
                    "close_price":  _float(row.iloc[2]),
                })
            logger.info("候选池扫描 threshold=%.0f%%: %d只", threshold, len(result))
            return result
        except Exception as exc:
            logger.error("候选池扫描失败: %s", exc)
            return []

    def get_gem_limit_up_stocks(self, date_str: str) -> list[dict[str, Any]]:
        """
        获取今日涨停创业板股票。
        优先用新浪实时行情（stock_zh_a_spot），东方财富接口不可用时自动降级。
        涨停判定：创业板代码（sz3开头）且涨跌幅 >= 19%。
        """
        import akshare as ak

        # ── 方案A：新浪实时行情（主用）────────────────────────
        try:
            df = ak.stock_zh_a_spot()
            # 列顺序：[0]=symbol  [1]=name  [2]=trade  [4]=changepercent
            gem_limit = df[
                df.iloc[:, 0].str.startswith("sz3") &
                (df.iloc[:, 4] >= 19.0)
            ]
            result = []
            for _, row in gem_limit.iterrows():
                sym = str(row.iloc[0])           # sz300715
                code6 = sym[2:]                  # 300715
                result.append({
                    "code": f"{code6}.SZ",
                    "name": str(row.iloc[1]),
                    "consecutive_boards": 1,      # 新浪无连板数，默认1
                })
            logger.info("新浪涨停板：创业板涨停 %d 只", len(result))
            return result
        except Exception as exc:
            logger.warning("新浪涨停检测失败: %s，尝试东方财富", exc)

        # ── 方案B：东方财富（备用）──────────────────────────
        date_fmt = date_str.replace("-", "")
        try:
            df2 = ak.stock_zt_pool_em(date=date_fmt)
            result = []
            for _, row in df2.iterrows():
                code6 = str(row.get("代码", ""))
                if not any(code6.startswith(p) for p in _GEM_PREFIXES):
                    continue
                result.append({
                    "code": f"{code6}.SZ",
                    "name": str(row.get("名称", "")),
                    "consecutive_boards": int(row.get("连板数", 1)),
                })
            return result
        except Exception as exc2:
            logger.error("东方财富涨停板也不可用: %s", exc2)
            return []

    def get_gem_stocks(self, date_str: str) -> list[dict[str, str]]:
        return [
            {"code": s["code"], "name": s["name"]}
            for s in self.get_gem_limit_up_stocks(date_str)
        ]

    # ── 历史日线（新浪财经，稳定可用）────────────────────────────

    def get_daily_batch(
        self, codes: list[str], start_date: str, end_date: str
    ) -> dict[str, list[dict[str, Any]]]:
        """
        逐只股票拉取日线（新浪财经）。
        返回 {code: [{date, open, high, low, close, change_ratio, volume}, ...]}
        """
        import akshare as ak

        start_fmt = start_date.replace("-", "")
        end_fmt = end_date.replace("-", "")
        result: dict[str, list[dict[str, Any]]] = {}

        for code in codes:
            sina_sym = _to_sina(code)
            try:
                df = ak.stock_zh_a_daily(
                    symbol=sina_sym,
                    start_date=start_fmt,
                    end_date=end_fmt,
                    adjust="",
                )
                if df is None or df.empty:
                    result[code] = []
                    continue

                bars: list[dict[str, Any]] = []
                for _, row in df.iterrows():
                    prev_close = bars[-1]["close"] if bars else None
                    chg = (
                        round((row["close"] - prev_close) / prev_close * 100, 2)
                        if prev_close and prev_close > 0 else None
                    )
                    bars.append({
                        "date": str(row["date"])[:10],
                        "open":  _float(row["open"]),
                        "high":  _float(row["high"]),
                        "low":   _float(row["low"]),
                        "close": _float(row["close"]),
                        "change_ratio": chg,
                        "volume": _float(row.get("volume")),
                        "amount": _float(row.get("amount")),
                    })
                result[code] = bars          # 已按日期升序
            except Exception as exc:
                logger.warning("新浪日线失败 code=%s: %s", code, exc)
                result[code] = []

        return result

    # ── 实时行情（新浪财经）──────────────────────────────────────

    def get_realtime_batch(self, codes: list[str]) -> dict[str, dict[str, Any]]:
        """
        一次拉取全市场实时行情（新浪），按传入 codes 过滤。

        新浪 stock_zh_a_spot 列顺序（按索引）：
          0=symbol, 1=name, 2=trade(最新), 3=pricechange(涨跌额),
          4=changepercent(涨跌幅%), 5=buy(买一), 6=sell(卖一),
          7=settlement(昨收), 8=open(今开), 9=high, 10=low,
          11=volume(手), 12=amount(元), 13=ticktime
        """
        import akshare as ak
        try:
            df = ak.stock_zh_a_spot()
        except Exception as exc:
            logger.error("新浪实时行情失败: %s", exc)
            return {}

        result: dict[str, dict[str, Any]] = {}
        for code in codes:
            sina_sym = _to_sina(code)
            rows = df[df.iloc[:, 0] == sina_sym]
            if rows.empty:
                continue
            row = rows.iloc[0]
            result[code] = {
                "latest":       _float(row.iloc[2]),   # trade
                "change_ratio": _float(row.iloc[4]),   # changepercent
                "open":         _float(row.iloc[8]),   # open
                "high":         _float(row.iloc[9]),   # high
                "low":          _float(row.iloc[10]),  # low
            }
        return result

    # ── 今日分钟数据（实时折线图）──────────────────────────────

    def get_intraday(self, code: str) -> list[dict[str, Any]]:
        """
        今日1分钟K线（新浪财经）。
        列名：day, open, high, low, close, volume, amount
        """
        import akshare as ak
        from datetime import date as _date
        today = _date.today().strftime("%Y-%m-%d")
        sina_sym = _to_sina(code)
        try:
            df = ak.stock_zh_a_minute(symbol=sina_sym, period="1", adjust="")
            if df is None or df.empty:
                return []

            # 时间列名：'day'（格式 2026-05-14 09:31:00）
            time_col = "day" if "day" in df.columns else df.columns[0]

            # 优先取今天；若无数据（非交易日）取最近一个交易日
            today_df = df[df[time_col].astype(str).str.startswith(today)]
            if today_df.empty:
                # 取最后一个交易日（最后出现的日期前缀）
                last_date = str(df[time_col].iloc[-1])[:10]
                today_df = df[df[time_col].astype(str).str.startswith(last_date)]

            result = []
            for _, row in today_df.iterrows():
                t = str(row[time_col])
                result.append({
                    "time":   t[11:16] if len(t) > 10 else t,
                    "open":   _float(row.get("open",  row.get("开盘"))),
                    "close":  _float(row.get("close", row.get("收盘"))),
                    "high":   _float(row.get("high",  row.get("最高"))),
                    "low":    _float(row.get("low",   row.get("最低"))),
                    "volume": _float(row.get("volume", row.get("成交量"))),
                })
            return result
        except Exception as exc:
            logger.warning("新浪分钟数据失败 code=%s: %s", code, exc)
            return []

    # ── 股票名称查询 ────────────────────────────────────────────

    def get_stock_name(self, code: str) -> str | None:
        """根据代码查询真实股票名称（300720.SZ → '海川智能'）"""
        import akshare as ak
        code6 = _to_ak(code)
        try:
            df = ak.stock_info_a_code_name()
            rows = df[df["code"] == code6]
            if not rows.empty:
                return str(rows.iloc[0]["name"])
        except Exception as exc:
            logger.warning("查询股票名称失败 code=%s: %s", code, exc)
        return None

    def batch_get_names(self, codes: list[str]) -> dict[str, str]:
        """批量查询股票名称，返回 {code: name}"""
        import akshare as ak
        try:
            df = ak.stock_info_a_code_name()
            code6_map = {_to_ak(c): c for c in codes}
            result = {}
            for _, row in df.iterrows():
                c6 = str(row["code"])
                if c6 in code6_map:
                    result[code6_map[c6]] = str(row["name"])
            return result
        except Exception as exc:
            logger.warning("批量查询名称失败: %s", exc)
            return {}

    # ── 兼容直接查询 ────────────────────────────────────────────

    def get_stock_daily(self, code: str, date_str: str) -> dict[str, Any]:
        data = self.get_daily_batch([code], date_str, date_str)
        bars = data.get(code, [])
        return {"tables": [{"thscode": code, **bars[0]}] if bars else []}

    def get_realtime_quote(self, code: str) -> dict[str, Any]:
        data = self.get_realtime_batch([code])
        return {"tables": [{"thscode": code, **data[code]}] if code in data else []}
