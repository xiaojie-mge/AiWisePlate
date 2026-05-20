"""Stock monitoring data — SQLite, per-user isolation."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "stock_data.db"


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS stock_pool (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            code         TEXT NOT NULL,
            name         TEXT,
            add_type     TEXT DEFAULT 'manual',
            trade_status TEXT DEFAULT 'pending',
            theme        TEXT,
            add_date     TEXT,
            status       TEXT DEFAULT 'in',
            UNIQUE(user_id, code)
        );
        CREATE TABLE IF NOT EXISTS candidate_pool (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            code         TEXT NOT NULL,
            name         TEXT,
            add_date     TEXT,
            change_ratio REAL,
            close_price  REAL,
            pool_status  TEXT DEFAULT 'pending'
        );
        CREATE TABLE IF NOT EXISTS buy_signal (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            code          TEXT NOT NULL,
            signal_date   TEXT,
            trigger_price REAL,
            ma5           REAL,
            is_notified   INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS position (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            code        TEXT NOT NULL,
            name        TEXT,
            buy_date    TEXT,
            buy_price   REAL,
            shares      INTEGER DEFAULT 100,
            status      TEXT DEFAULT 'open',
            close_date  TEXT,
            close_price REAL,
            pnl         REAL,
            pnl_pct     REAL,
            break_date  TEXT
        );
        CREATE TABLE IF NOT EXISTS break_board (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL,
            code             TEXT NOT NULL,
            break_date       TEXT NOT NULL,
            prev_limit_price REAL,
            median_price     REAL,
            monitor_end_date TEXT,
            UNIQUE(user_id, code, break_date)
        );
        CREATE TABLE IF NOT EXISTS sell_alert (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            position_id INTEGER NOT NULL,
            code        TEXT,
            action      TEXT,
            reason      TEXT,
            latest      REAL,
            pnl_pct     REAL,
            alert_time  TEXT,
            is_read     INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS user_session (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            session_id TEXT NOT NULL UNIQUE,
            title      TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS user_run (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            run_id  TEXT NOT NULL UNIQUE,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS realtime_cache (
            code        TEXT PRIMARY KEY,
            name        TEXT,
            price       REAL,
            change_pct  REAL,
            open_price  REAL,
            high        REAL,
            low         REAL,
            pre_close   REAL,
            volume      REAL,
            amount      REAL,
            market      TEXT,
            updated_at  TEXT
        );
        """)
        c.commit()


init_db()


def add_to_pool(user_id: int, code: str, name: str = "") -> None:
    import time
    today = time.strftime("%Y-%m-%d")
    with _conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO stock_pool (user_id,code,name,add_type,add_date) VALUES (?,?,?,?,?)",
            (user_id, code, name, "manual", today)
        )
        c.commit()


def get_pool(user_id: int) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM stock_pool WHERE user_id=? AND status='in' ORDER BY add_date DESC",
            (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_candidates(user_id: int) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM candidate_pool WHERE user_id=? AND pool_status='pending' ORDER BY change_ratio DESC",
            (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def select_candidate(cid: int, user_id: int) -> None:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM candidate_pool WHERE id=? AND user_id=?", (cid, user_id)
        ).fetchone()
        if not row:
            return
        today = time.strftime("%Y-%m-%d")
        c.execute(
            "INSERT OR IGNORE INTO stock_pool (user_id,code,name,add_type,add_date) VALUES (?,?,?,?,?)",
            (user_id, row["code"], row["name"], "auto", today)
        )
        c.execute("UPDATE candidate_pool SET pool_status='selected' WHERE id=?", (cid,))
        c.commit()


def get_signals(user_id: int) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM buy_signal WHERE user_id=? ORDER BY signal_date DESC LIMIT 50",
            (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_positions(user_id: int) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM position WHERE user_id=? ORDER BY buy_date DESC",
            (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]
