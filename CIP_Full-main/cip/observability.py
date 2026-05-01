"""Observability helpers for CIP."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .db import execute, fetch_all, init_db


def _now() -> str:
    return datetime.utcnow().isoformat()


async def log_event(session_id: str, user_id: str | None, event_type: str, payload: Any) -> None:
    await execute(
        "INSERT INTO events (session_id, user_id, event_type, payload, created_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, user_id, event_type, json.dumps(payload, ensure_ascii=False, default=str), _now()),
    )


async def log_trace(
    session_id: str,
    trace_type: str,
    actor: str,
    description: str,
    inputs: Any = None,
    outputs: Any = None,
    reasoning: str | None = None,
) -> None:
    await execute(
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
            json.dumps(inputs, ensure_ascii=False, default=str) if inputs is not None else None,
            json.dumps(outputs, ensure_ascii=False, default=str) if outputs is not None else None,
            reasoning,
            _now(),
        ),
    )


async def log_proto(
    session_id: str,
    action: str,
    actor: str = "system",
    message: str = "",
    payload: Any = None,
    level: str = "INFO",
    status: str = "ok",
) -> None:
    await execute(
        """
        INSERT INTO session_logs (session_id, level, action, actor, status, message, payload, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            level,
            action,
            actor,
            status,
            message,
            json.dumps(payload, ensure_ascii=False, default=str) if payload is not None else None,
            _now(),
        ),
    )


async def log_proto_exception(session_id: str, action: str, actor: str, exc: Exception, payload: Any = None) -> None:
    await log_proto(
        session_id=session_id,
        action=action,
        actor=actor,
        message=str(exc),
        payload=payload,
        level="ERROR",
        status="error",
    )
    await log_trace(
        session_id=session_id,
        trace_type="proto.error",
        actor=actor,
        description=action,
        inputs=payload,
        outputs={"error": str(exc)},
        reasoning="Exception captured by prototype logger",
    )


async def export_session_transcript(session_id: str) -> str:
    rows = await fetch_all(
        "SELECT payload, created_at FROM events WHERE session_id = ? AND event_type = 'message' ORDER BY created_at",
        (session_id,),
    )
    lines: list[str] = []
    for row in rows:
        payload = json.loads(row["payload"])
        lines.append(f"{row['created_at']} - **{payload.get('user_id', 'unknown')}**: {payload.get('text', '')}")
    return "\n".join(lines)


async def export_session_traces(session_id: str) -> str:
    rows = await fetch_all("SELECT * FROM traces WHERE session_id = ? ORDER BY created_at", (session_id,))
    return "\n\n".join(json.dumps(row, indent=2, ensure_ascii=False) for row in rows)


async def export_session_replay(session_id: str) -> dict:
    events = await fetch_all("SELECT * FROM events WHERE session_id = ? ORDER BY created_at", (session_id,))
    traces = await fetch_all("SELECT * FROM traces WHERE session_id = ? ORDER BY created_at", (session_id,))
    return {"events": events, "traces": traces}
