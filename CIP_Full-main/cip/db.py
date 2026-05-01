"""Async SQLite helpers and schema for CIP."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import aiosqlite

DB_PATH = Path("cip.sqlite3")


async def init_db(db_path: Optional[Path] = None) -> None:
    """Initialise all tables used by the prototype, simulator and AI pipeline."""
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
                participant_type TEXT NOT NULL DEFAULT 'participant',
                display_name TEXT,
                last_seen_at TEXT,
                created_at TEXT NOT NULL,
                PRIMARY KEY (id, session_id)
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                participant_id TEXT NOT NULL,
                text TEXT NOT NULL,
                participant_type TEXT NOT NULL DEFAULT 'participant',
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
                participant_id TEXT,
                text TEXT NOT NULL,
                theme TEXT,
                quality_score REAL DEFAULT 0,
                source_message_id INTEGER,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS clusters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                label TEXT NOT NULL,
                size INTEGER DEFAULT 0,
                payload TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS injections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL DEFAULT 'prompt',
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
                actor TEXT,
                status TEXT,
                message TEXT,
                payload TEXT,
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
            """
        )
        await db.commit()


async def execute(sql: str, params: tuple[Any, ...] = ()) -> int:
    """Execute SQL and return lastrowid when available."""
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(sql, params)
        await db.commit()
        return int(cur.lastrowid or 0)


async def fetch_one(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(sql, params)
        row = await cur.fetchone()
        return dict(row) if row else None


async def fetch_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(sql, params)
        rows = await cur.fetchall()
        return [dict(row) for row in rows]


class DBFacade:
    """Small compatibility wrapper for existing route code."""
    async def execute(self, sql: str, *args: Any) -> int:
        return await execute(_normalize_sql(sql), tuple(args))

    async def fetch_one(self, sql: str, *args: Any) -> dict[str, Any] | None:
        return await fetch_one(_normalize_sql(sql), tuple(args))

    async def fetch_all(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        return await fetch_all(_normalize_sql(sql), tuple(args))


class _DBContext:
    async def __aenter__(self) -> DBFacade:
        await init_db()
        return DBFacade()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


def get_db(db_path: Optional[Path] = None) -> _DBContext:
    return _DBContext()


def _normalize_sql(sql: str) -> str:
    """Compatibility for old asyncpg-style placeholders and NOW()."""
    out = sql.replace("NOW()", "datetime('now')")
    for i in range(1, 20):
        out = out.replace(f"${i}", "?")
    return out


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)
