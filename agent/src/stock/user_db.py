"""Multi-user management with SQLite."""
from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
import time
import base64
import json
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parents[2] / "stock_users.db"
_SECRET = os.getenv("STOCK_JWT_SECRET", "vibe-stock-secret-2026")
_TOKEN_TTL = 8 * 3600  # 8 hours


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables and default admin user."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT UNIQUE NOT NULL,
                pwd_hash    TEXT NOT NULL,
                role        TEXT NOT NULL DEFAULT 'user',
                display     TEXT,
                created     INTEGER NOT NULL,
                can_ai      INTEGER DEFAULT 1,
                can_backtest INTEGER DEFAULT 1,
                can_stock   INTEGER DEFAULT 1,
                is_active   INTEGER DEFAULT 1
            )
        """)
        conn.commit()
        # Create default admin if no users exist
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            _create_user_inner(conn, "admin", "Admin@123", "admin", "管理员")
            conn.commit()


def _hash_pwd(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _create_user_inner(conn, username: str, password: str, role: str, display: str) -> None:
    conn.execute(
        "INSERT INTO users (username, pwd_hash, role, display, created) VALUES (?,?,?,?,?)",
        (username, _hash_pwd(password), role, display or username, int(time.time())),
    )


# ── Public API ────────────────────────────────────────────────────────────────

def verify_login(username: str, password: str) -> Optional[dict]:
    """Return user dict if credentials valid, else None."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username=?", (username,)
        ).fetchone()
    if row and hmac.compare_digest(row["pwd_hash"], _hash_pwd(password)):
        return dict(row)
    return None


def create_user(username: str, password: str, role: str = "user", display: str = "") -> dict:
    with _get_conn() as conn:
        _create_user_inner(conn, username, password, role, display or username)
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    return dict(row)


def list_users() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT id,username,role,display,created FROM users ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def delete_user(username: str) -> bool:
    """删除用户，admin 账户不可删除。"""
    with _get_conn() as conn:
        # 检查是否为唯一 admin
        target = conn.execute("SELECT role FROM users WHERE username=?", (username,)).fetchone()
        if not target:
            return False
        if target["role"] == "admin":
            return False  # admin 不可删除
        cur = conn.execute("DELETE FROM users WHERE username=?", (username,))
        conn.commit()
    return cur.rowcount > 0


def update_user_permissions(username: str, permissions: dict) -> bool:
    """更新用户权限（role/can_ai/can_backtest/can_stock/is_active）。"""
    allowed = {"role", "can_ai", "can_backtest", "can_stock", "is_active", "display"}
    updates = {k: v for k, v in permissions.items() if k in allowed}
    if not updates:
        return False
    with _get_conn() as conn:
        target = conn.execute("SELECT role FROM users WHERE username=?", (username,)).fetchone()
        if not target:
            return False
        # 不允许降级唯一 admin 的 role
        if target["role"] == "admin" and updates.get("role") == "user":
            admin_count = conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]
            if admin_count <= 1:
                updates.pop("role")  # 不允许降级
        sets = ", ".join(f"{k}=?" for k in updates)
        vals = list(updates.values()) + [username]
        conn.execute(f"UPDATE users SET {sets} WHERE username=?", vals)
        conn.commit()
    return True


def change_password(username: str, new_password: str) -> bool:
    with _get_conn() as conn:
        cur = conn.execute(
            "UPDATE users SET pwd_hash=? WHERE username=?",
            (_hash_pwd(new_password), username),
        )
        conn.commit()
    return cur.rowcount > 0


# ── JWT ───────────────────────────────────────────────────────────────────────

def _sign(data: str) -> str:
    return hmac.new(_SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()


def create_token(user: dict) -> str:
    payload = {
        "uid": user["id"],
        "u": user["username"],
        "role": user["role"],
        "exp": int(time.time()) + _TOKEN_TTL,
    }
    data = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    return f"{data}.{_sign(data)}"


def verify_token(token: str) -> Optional[dict]:
    try:
        data, sig = token.rsplit(".", 1)
        if not hmac.compare_digest(_sign(data), sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(data).decode())
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None
