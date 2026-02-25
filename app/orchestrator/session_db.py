import sqlite3
from pathlib import Path


class SQLiteSessionDB:
    def __init__(self):
        self.db_path = Path(__file__).resolve().parent.parent.parent / "sessions.db"
        self._ensure_table()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_active_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def upsert(self, session_id: str, data_json: str, created_at: str, last_active_at: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, data, created_at, last_active_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    data=excluded.data,
                    last_active_at=excluded.last_active_at
                """,
                (session_id, data_json, created_at, last_active_at),
            )
            conn.commit()

    def get(self, session_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT session_id, data, created_at, last_active_at FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            return dict(row) if row else None
