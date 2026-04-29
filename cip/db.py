"""Database helpers for CIP v2.

The app uses SQLite through aiosqlite.  The schema below intentionally keeps a
small set of pilot-ready tables so that the UI pages can work immediately:
sessions, participants, messages, events, traces, ideas, clusters and injections.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

import aiosqlite

DB_PATH = Path("cip.sqlite3")


async def init_db(db_path: Optional[Path] = None) -> None:
    """Initialise the SQLite database and create/upgrade required tables."""
    path = db_path or DB_PATH
    async with aiosqlite.connect(path) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
              id TEXT PRIMARY KEY,
              status TEXT NOT NULL DEFAULT 'active',
              current_phase TEXT NOT NULL DEFAULT 'clarification',
              topic TEXT,
              config TEXT,
              duration_seconds INTEGER DEFAULT 0,
              created_at TEXT NOT NULL,
              updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS participants (
              id TEXT NOT NULL,
              session_id TEXT NOT NULL,
              participant_type TEXT DEFAULT 'participant',
              display_name TEXT,
              created_at TEXT NOT NULL,
              last_seen_at TEXT,
              PRIMARY KEY (id, session_id)
            );

            CREATE TABLE IF NOT EXISTS messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT NOT NULL,
              participant_id TEXT NOT NULL,
              text TEXT NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT NOT NULL,
              user_id TEXT,
              event_type TEXT NOT NULL,
              payload TEXT NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ideas (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT NOT NULL,
              text TEXT NOT NULL,
              theme TEXT DEFAULT 'general',
              quality_score REAL DEFAULT 0,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS clusters (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT NOT NULL,
              label TEXT NOT NULL,
              size INTEGER DEFAULT 0,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS injections (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT NOT NULL,
              content TEXT NOT NULL,
              content_type TEXT DEFAULT 'prompt',
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS llm_cache (
              prompt_hash TEXT PRIMARY KEY,
              response TEXT NOT NULL,
              tier TEXT,
              provider TEXT,
              model TEXT,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS session_configs (
              session_id TEXT PRIMARY KEY,
              config TEXT NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS traces (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT NOT NULL,
              trace_type TEXT NOT NULL,
              actor TEXT NOT NULL,
              description TEXT NOT NULL,
              inputs TEXT,
              outputs TEXT,
              reasoning TEXT,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS session_logs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT NOT NULL,
              level TEXT NOT NULL DEFAULT 'INFO',
              action TEXT NOT NULL,
              actor TEXT NOT NULL DEFAULT 'system',
              status TEXT NOT NULL DEFAULT 'ok',
              message TEXT NOT NULL,
              payload TEXT,
              error TEXT,
              created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_session_logs_session_time
              ON session_logs (session_id, created_at);

            CREATE INDEX IF NOT EXISTS idx_traces_session_time
              ON traces (session_id, created_at);

            CREATE INDEX IF NOT EXISTS idx_events_session_time
              ON events (session_id, created_at);
            """
        )
        await db.commit()


@asynccontextmanager
async def get_db(db_path: Optional[Path] = None) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Yield a database connection that automatically closes when done."""
    path = db_path or DB_PATH
    db = await aiosqlite.connect(path)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    """Return all rows as dictionaries."""
    async with get_db() as db:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        await cursor.close()
        return [dict(row) for row in rows]


async def fetch_one(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    """Return one row as a dictionary, or None."""
    async with get_db() as db:
        cursor = await db.execute(query, params)
        row = await cursor.fetchone()
        await cursor.close()
        return dict(row) if row else None


async def execute(query: str, params: tuple[Any, ...] = ()) -> None:
    """Execute a write query and commit it."""
    async with get_db() as db:
        await db.execute(query, params)
        await db.commit()
