"""APScheduler 定时任务 — 断板识别、买卖点监控、候选池扫描。"""
from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_scheduler = None


def get_scheduler():
    global _scheduler
    if _scheduler is None:
        from apscheduler.schedulers.background import BackgroundScheduler
        _scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    return _scheduler


def start_scheduler() -> None:
    """在 FastAPI startup 时调用。"""
    from src.stock.user_db import DB_PATH as USER_DB
    from src.stock.stock_db import DB_PATH as STOCK_DB

    scheduler = get_scheduler()
    if scheduler.running:
        return

    # 盘中轮询：每30秒（仅交易时段执行）
    scheduler.add_job(
        _intraday_job, "interval", seconds=30,
        id="intraday", replace_existing=True
    )

    # 收盘后任务：周一至周五 16:35
    scheduler.add_job(
        _after_market_job, "cron",
        day_of_week="mon-fri", hour=16, minute=35,
        id="after_market", replace_existing=True
    )

    # 每天凌晨2点清理超过30天的旧会话
    scheduler.add_job(
        _cleanup_old_sessions, "cron",
        hour=2, minute=0,
        id="cleanup_sessions", replace_existing=True
    )

    # 每天6:00清空实时数据缓存
    scheduler.add_job(
        _clear_realtime_cache, "cron",
        hour=6, minute=0,
        id="clear_realtime", replace_existing=True
    )

    # 8:30-15:05 每30秒拉取入池股票实时数据
    scheduler.add_job(
        _pull_realtime, "interval", seconds=30,
        id="pull_realtime", replace_existing=True
    )

    scheduler.start()
    logger.info("股票监控定时任务已启动")


def stop_scheduler() -> None:
    """在 FastAPI shutdown 时调用。"""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("定时任务已停止")


def _get_conn():
    from src.stock.stock_db import _conn
    return _conn()


def _intraday_job() -> None:
    """盘中每30秒：买点监控 + 卖点监控。"""
    from src.stock.services.data_client import is_market_open
    if not is_market_open():
        return

    try:
        conn = _get_conn()
        from src.stock.services.buy_signal import check_buy_signals
        from src.stock.services.sell_signal import check_sell_signals
        buy_results = check_buy_signals(conn)
        sell_results = check_sell_signals(conn)
        if buy_results:
            logger.info("盘中买点触发 %d 条", len(buy_results))
        if sell_results:
            logger.info("盘中卖点提醒 %d 条", len(sell_results))
    except Exception as e:
        logger.error("intraday_job error: %s", e)


def _after_market_job() -> None:
    """收盘后 16:35：刷新策略池 + 断板识别 + 候选池扫描。"""
    logger.info("收盘后任务开始 %s", datetime.now().strftime("%H:%M"))
    try:
        conn = _get_conn()
        from src.stock.services.candidate_pool import refresh_stock_pool, refresh_candidate_pool
        from src.stock.services.break_board import detect_break_boards

        refresh_stock_pool(conn)
        detect_break_boards(conn)
        refresh_candidate_pool(conn)
        logger.info("收盘后任务完成")
    except Exception as e:
        logger.error("after_market_job error: %s", e)


def _clear_realtime_cache() -> None:
    """每天6:00清空实时数据缓存。"""
    try:
        from src.stock.services.realtime_service import clear_realtime_cache
        clear_realtime_cache(_get_conn())
    except Exception as e:
        logger.error("clear_realtime_cache error: %s", e)


def _pull_realtime() -> None:
    """8:30-15:05 每30秒拉取入池股票实时数据。"""
    from src.stock.services.realtime_service import is_pull_time, pull_realtime_for_pool
    if not is_pull_time():
        return
    try:
        pull_realtime_for_pool(_get_conn())
    except Exception as e:
        logger.error("pull_realtime error: %s", e)


def _cleanup_old_sessions() -> None:
    """清理超过30天的旧会话文件和记录。"""
    import time
    from pathlib import Path
    conn = _get_conn()
    cutoff = int(time.time()) - 30 * 86400  # 30天前
    # 查出旧会话
    old = conn.execute(
        "SELECT session_id FROM user_session WHERE created_at < datetime(?, 'unixepoch')",
        (cutoff,)
    ).fetchall()
    sessions_dir = Path(__file__).resolve().parents[3] / "sessions"
    removed = 0
    for row in old:
        sid = row["session_id"]
        # 删除会话目录
        sd = sessions_dir / sid
        if sd.exists():
            import shutil
            shutil.rmtree(sd, ignore_errors=True)
        conn.execute("DELETE FROM user_session WHERE session_id=?", (sid,))
        removed += 1
    conn.commit()
    if removed:
        logger.info("清理过期会话 %d 个", removed)


def manual_trigger_after_market() -> dict:
    """API 手动触发收盘任务（测试用）。"""
    try:
        conn = _get_conn()
        from src.stock.services.candidate_pool import refresh_stock_pool, refresh_candidate_pool
        from src.stock.services.break_board import detect_break_boards
        refresh_stock_pool(conn)
        breaks = detect_break_boards(conn)
        candidates = refresh_candidate_pool(conn)
        return {"status": "ok", "breaks": len(breaks), "candidates": len(candidates)}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
