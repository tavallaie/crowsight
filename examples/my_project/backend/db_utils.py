# my_project/backend/db_utils.py
import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "app.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_user_by_id(user_id: int, user_auth: str):
    print(user_auth)
    with get_connection() as conn:
        cur = conn.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None
