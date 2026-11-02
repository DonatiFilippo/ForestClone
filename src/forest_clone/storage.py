"""Local SQLite persistence. No network or external database required."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
import time
from typing import Iterator


class Storage:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self._migrate()

    def _migrate(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY,
                started_at REAL NOT NULL,
                duration_seconds INTEGER NOT NULL CHECK(duration_seconds > 0),
                status TEXT NOT NULL CHECK(status IN
                    ('running', 'paused', 'completed', 'interrupted')),
                deadline REAL,
                remaining_seconds REAL NOT NULL,
                ended_at REAL,
                tree_type TEXT NOT NULL DEFAULT 'peach'
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_session
                ON sessions((1)) WHERE status IN ('running', 'paused');
            CREATE INDEX IF NOT EXISTS sessions_started_at
                ON sessions(started_at DESC);
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        columns = {
            str(row[1]) for row in self.connection.execute("PRAGMA table_info(sessions)")
        }
        if "tree_type" not in columns:
            self.connection.execute(
                "ALTER TABLE sessions ADD COLUMN tree_type TEXT NOT NULL DEFAULT 'peach'"
            )
        self.connection.commit()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            with self.connection:
                yield self.connection
        except sqlite3.Error as error:
            raise RuntimeError(f"Could not save application data: {error}") from error

    def create_session(
        self,
        started_at: float,
        duration_seconds: int,
        deadline: float,
        tree_type: str = "peach",
    ) -> int:
        if tree_type not in ("peach", "pine"):
            raise ValueError("tree_type must be 'peach' or 'pine'")
        with self.transaction() as connection:
            cursor = connection.execute(
                """INSERT INTO sessions
                   (started_at, duration_seconds, status, deadline, remaining_seconds, tree_type)
                   VALUES (?, ?, 'running', ?, ?, ?)""",
                (started_at, duration_seconds, deadline, duration_seconds, tree_type),
            )
        return int(cursor.lastrowid)

    def update_active(
        self,
        session_id: int,
        status: str,
        deadline: float | None,
        remaining_seconds: float,
    ) -> None:
        if status not in ("running", "paused"):
            raise ValueError("invalid active status")
        with self.transaction() as connection:
            connection.execute(
                """UPDATE sessions SET status=?, deadline=?, remaining_seconds=?
                   WHERE id=? AND status IN ('running', 'paused')""",
                (status, deadline, remaining_seconds, session_id),
            )

    def finish_session(
        self,
        session_id: int,
        completed: bool,
        ended_at: float | None = None,
        remaining_seconds: float | None = None,
    ) -> bool:
        """Finish once. Returns False when session was already finalized."""
        status = "completed" if completed else "interrupted"
        remaining = (
            0.0
            if completed
            else remaining_seconds
            if remaining_seconds is not None
            else self._remaining_for(session_id)
        )
        with self.transaction() as connection:
            cursor = connection.execute(
                """UPDATE sessions
                   SET status=?, deadline=NULL, remaining_seconds=?, ended_at=?
                   WHERE id=? AND status IN ('running', 'paused')""",
                (status, remaining, ended_at or time.time(), session_id),
            )
        return cursor.rowcount == 1

    def _remaining_for(self, session_id: int) -> float:
        row = self.connection.execute(
            "SELECT remaining_seconds FROM sessions WHERE id=?", (session_id,)
        ).fetchone()
        return float(row[0]) if row else 0.0

    def active_session(self) -> sqlite3.Row | None:
        return self.connection.execute(
            """SELECT * FROM sessions
               WHERE status IN ('running', 'paused') LIMIT 1"""
        ).fetchone()

    def sessions(self, limit: int | None = None) -> list[sqlite3.Row]:
        sql = "SELECT * FROM sessions ORDER BY started_at DESC"
        params: tuple[int, ...] = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (limit,)
        return list(self.connection.execute(sql, params))

    def completed_sessions(self) -> list[sqlite3.Row]:
        return list(
            self.connection.execute(
                "SELECT * FROM sessions WHERE status='completed' ORDER BY started_at"
            )
        )

    def get_setting(self, key: str, default: str) -> str:
        row = self.connection.execute(
            "SELECT value FROM settings WHERE key=?", (key,)
        ).fetchone()
        return str(row[0]) if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.transaction() as connection:
            connection.execute(
                """INSERT INTO settings(key, value) VALUES (?, ?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                (key, value),
            )

    def close(self) -> None:
        self.connection.close()
