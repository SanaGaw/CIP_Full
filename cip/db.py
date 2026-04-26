"""Database helpers for CIP v2.

This module provides functions to initialise the SQLite database and to obtain
connections. It uses `aiosqlite` for async interactions. The database stores
events, LLM cache entries, session configurations and traces.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

try:
    import aiosqlite  # type: ignore
except ImportError:
    # Provide a minimal fallback implementation of aiosqlite using sqlite3.
    import sqlite3
    import types
    class _CursorWrapper:
        def __init__(self, cursor: sqlite3.Cursor) -> None:
            self._cursor = cursor
            self.description = cursor.description
        def __aiter__(self):
            self._iter = iter(self._cursor)
            return self
        async def __anext__(self):
            try:
                return next(self._iter)
            except StopIteration:
                raise StopAsyncIteration
        def __iter__(self):
            return iter(self._cursor)
        def __next__(self):
            return next(self._cursor)
        def __getitem__(self, key):
            return self._cursor[key]

    class _ConnectionWrapper:
        def __init__(self, conn: sqlite3.Connection) -> None:
            self._conn = conn
            self.row_factory = sqlite3.Row
        async def execute(self, sql: str, params=()):
            cur = self._conn.cursor()
            cur.execute(sql, params)
            return _CursorWrapper(cur)
        async def executescript(self, script: str):
            cur = self._conn.cursor()
            cur.executescript(script)
            return cur
        async def commit(self):
            self._conn.commit()
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            self._conn.close()
        def __getattr__(self, name):
            return getattr(self._conn, name)

    class _aiosqlite_module(types.SimpleNamespace):
        Row = sqlite3.Row
        async def connect(self, path):
            conn = sqlite3.connect(path)
            conn.row_factory = sqlite3.Row
            return _ConnectionWrapper(conn)

    aiosqlite = _aiosqlite_module()

DB_PATH = Path("cip.sqlite3")


async def init_db(db_path: Optional[Path] = None) -> None:
    """Initialise the SQLite database and create required tables.

    Args:
        db_path: Optional path to the SQLite file. Defaults to `DB_PATH`.
    """
    path = db_path or DB_PATH
    # Connect to the database. Some backends (the real aiosqlite) return an
    # asynchronous context manager, while our fallback returns a coroutine
    # yielding a wrapper that implements __aenter__/__aexit__. Normalising this
    # behaviour makes it safe to call across both implementations.
    conn_coro_or_manager = aiosqlite.connect(path)  # type: ignore[attr-defined]
    # If the returned object supports __aenter__, it is an async context
    # manager; otherwise it's a coroutine that yields a connection.
    if hasattr(conn_coro_or_manager, "__aenter__"):
        # Use async with directly
        async with conn_coro_or_manager as db:
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  session_id TEXT NOT NULL,
                  user_id TEXT,
                  event_type TEXT NOT NULL,
                  payload TEXT NOT NULL,
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
                """
            )
            await db.commit()
    else:
        # Await the coroutine to get a connection wrapper and manually commit
        db = await conn_coro_or_manager
        try:
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  session_id TEXT NOT NULL,
                  user_id TEXT,
                  event_type TEXT NOT NULL,
                  payload TEXT NOT NULL,
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
                """
            )
            await db.commit()
        finally:
            # Close connection gracefully
            close = getattr(db, "close", None)
            if close is not None:
                if asyncio.iscoroutinefunction(close):  # type: ignore[arg-type]
                    await close()
                else:
                    close()


@asynccontextmanager
async def get_db(db_path: Optional[Path] = None) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Yield a database connection that automatically closes when done.

    Usage:
        async with get_db() as db:
            await db.execute(...)

    Args:
        db_path: Optional path to the SQLite file. Defaults to `DB_PATH`.
    """
    path = db_path or DB_PATH
    conn = await aiosqlite.connect(path)  # type: ignore[attr-defined]
    # Some backends (fallback) set row_factory in __init__.
    try:
        conn.row_factory = aiosqlite.Row  # type: ignore[assignment]
    except Exception:
        pass
    try:
        yield conn
    finally:
        # Close the connection gracefully regardless of whether close is a coroutine or normal function.
        close = getattr(conn, "close", None)
        if close is not None:
            # If the close method is awaitable, await it; otherwise call it directly.
            if asyncio.iscoroutinefunction(close):  # type: ignore[arg-type]
                await close()
            else:
                close()