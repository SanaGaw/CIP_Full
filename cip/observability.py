"""Observability tools for CIP v2.

This module centralises logging of events and traces for debugging. It uses the
database layer to persist events and traces. The export functions can be used
to produce session transcripts and trace logs for post-hoc analysis.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .db import get_db, init_db


async def log_event(session_id: str, user_id: str | None, event_type: str, payload: Any) -> None:
    """Insert an event into the events table.

    Args:
        session_id: The session identifier.
        user_id: Optional user identifier.
        event_type: String describing the type of event.
        payload: Arbitrary JSON-serialisable payload.
    """
    # Ensure the database schema is initialised. This is idempotent and cheap because
    # the underlying SQL uses CREATE TABLE IF NOT EXISTS. Without this call the
    # events table may not exist when running unit tests, which can cause
    # OperationalError on insertion. See cip/db.py for init_db implementation.
    await init_db()
    ts = datetime.utcnow().isoformat()
    async with get_db() as db:
        await db.execute(
            "INSERT INTO events (session_id, user_id, event_type, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, user_id, event_type, json.dumps(payload), ts),
        )
        await db.commit()


async def log_trace(
    session_id: str,
    trace_type: str,
    actor: str,
    description: str,
    inputs: Any = None,
    outputs: Any = None,
    reasoning: str | None = None,
) -> None:
    """Insert a trace row into the traces table.

    Args:
        session_id: The session identifier.
        trace_type: The type of trace (decision, llm_call, etc.).
        actor: The actor producing the trace.
        description: Human-readable description of what happened.
        inputs: Optional inputs associated with the trace.
        outputs: Optional outputs associated with the trace.
        reasoning: Optional explanation of why this happened.
    """
    # Ensure the database schema is initialised to avoid missing table errors.
    await init_db()
    ts = datetime.utcnow().isoformat()
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO traces
              (session_id, trace_type, actor, description, inputs, outputs, reasoning, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                trace_type,
                actor,
                description,
                json.dumps(inputs) if inputs is not None else None,
                json.dumps(outputs) if outputs is not None else None,
                reasoning,
                ts,
            ),
        )
        await db.commit()


async def export_session_transcript(session_id: str) -> str:
    """Return a Markdown transcript of a session's chat events.

    The transcript includes only events of type 'message'. The payload is
    expected to contain at least 'user_id' and 'text'.
    """
    lines: list[str] = []
    async with get_db() as db:
        async with db.execute(
            "SELECT payload, created_at FROM events WHERE session_id = ? AND event_type = 'message' ORDER BY created_at",
            (session_id,),
        ) as cursor:
            async for row in cursor:
                payload = json.loads(row["payload"])
                ts = row["created_at"]
                user = payload.get("user_id", "unknown")
                text = payload.get("text", "")
                lines.append(f"{ts} - **{user}**: {text}")
    return "\n".join(lines)


async def export_session_traces(session_id: str) -> str:
    """Return a Markdown representation of all traces for a session."""
    lines: list[str] = []
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM traces WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ) as cursor:
            cols = [column[0] for column in cursor.description]
            async for row in cursor:
                record = {col: row[col] for col in cols}
                lines.append(json.dumps(record, indent=2))
    return "\n\n".join(lines)


async def export_session_replay(session_id: str) -> dict:
    """Return a JSON object containing enough information to replay a session.

    For now this returns the event log and trace log; further fields can be
    added to support richer replay viewers.
    """
    async with get_db() as db:
        # Fetch events
        events: list[dict] = []
        async with db.execute(
            "SELECT * FROM events WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ) as cursor:
            cols = [column[0] for column in cursor.description]
            async for row in cursor:
                record = {col: row[col] for col in cols}
                record["payload"] = json.loads(record["payload"])
                events.append(record)
        # Fetch traces
        traces: list[dict] = []
        async with db.execute(
            "SELECT * FROM traces WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ) as cursor:
            cols = [column[0] for column in cursor.description]
            async for row in cursor:
                record = {col: row[col] for col in cols}
                traces.append(record)
    return {"events": events, "traces": traces}