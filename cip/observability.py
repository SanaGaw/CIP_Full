"""Observability tools for CIP v2.

This module centralises session observability. Normal session events such as
messages stay available for transcripts and replay. Verbose proto logs are
conditional: they are persisted only when PROTO_MODE=True and
PROTO_VERBOSE_LOGGING=True in `.env`.
"""
from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime
from typing import Any

from .config import get_settings
from .db import get_db, init_db

LOGGER = logging.getLogger("cip.proto")

_SECRET_TOKENS = ("api_key", "password", "token", "secret", "authorization", "bearer")


def _now() -> str:
    return datetime.utcnow().isoformat()


def proto_logging_enabled() -> bool:
    """Return True when verbose proto logging should persist data."""
    settings = get_settings()
    return bool(settings.proto_mode and settings.proto_verbose_logging)


def _json_default(value: Any) -> str:
    try:
        return str(value)
    except Exception:
        return "<unserializable>"


def _redact(value: Any) -> Any:
    """Redact obvious secrets before persisting debug payloads."""
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if any(token in key_text for token in _SECRET_TOKENS):
                redacted[key] = "***redacted***"
            else:
                redacted[key] = _redact(item)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in value)
    return value


def _to_json(value: Any) -> str | None:
    if value is None:
        return None
    settings = get_settings()
    max_chars = max(200, int(settings.proto_log_payload_max_chars or 4000))
    try:
        text = json.dumps(_redact(value), ensure_ascii=False, default=_json_default)
    except Exception:
        text = json.dumps({"serialization_error": _json_default(value)}, ensure_ascii=False)
    if len(text) > max_chars:
        text = text[:max_chars] + f"... <truncated to {max_chars} chars>"
    return text


def _console_log(level: str, message: str, payload: dict[str, Any] | None = None) -> None:
    settings = get_settings()
    if not settings.proto_log_to_console:
        return
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    LOGGER.log(numeric_level, "%s %s", message, _to_json(payload) or "")


async def log_event(session_id: str, user_id: str | None, event_type: str, payload: Any) -> None:
    """Insert a normal session event into the events table.

    Normal events are not gated by proto mode because the transcript and replay
    screens rely on them in every environment.
    """
    await init_db()
    ts = _now()
    async with get_db() as db:
        await db.execute(
            "INSERT INTO events (session_id, user_id, event_type, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, user_id, event_type, json.dumps(_redact(payload), ensure_ascii=False, default=_json_default), ts),
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
    """Insert a trace row when proto verbose logging is enabled.

    Existing agents already call this function. Gating it here guarantees that
    detailed traces are collected in prototype mode only.
    """
    if not proto_logging_enabled():
        return
    try:
        await init_db()
        ts = _now()
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
                    _to_json(inputs),
                    _to_json(outputs),
                    reasoning,
                    ts,
                ),
            )
            await db.commit()
    except Exception:
        LOGGER.exception("Failed to persist proto trace")


async def log_proto(
    session_id: str,
    action: str,
    actor: str = "system",
    message: str = "",
    level: str = "INFO",
    status: str = "ok",
    payload: Any = None,
    error: Any = None,
) -> None:
    """Persist a verbose proto session log if proto logging is enabled.

    Use this for every significant action: route called, session started,
    participant connected, message saved, phase changed, validation warning,
    broadcast failure, exception, etc. The function is defensive: logging must
    never break the actual application flow.
    """
    if not proto_logging_enabled():
        return

    level = (level or "INFO").upper()
    status = status or "ok"
    message = message or action
    ts = _now()
    safe_payload = _to_json(payload)
    safe_error = _to_json(error)

    try:
        await init_db()
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO session_logs
                  (session_id, level, action, actor, status, message, payload, error, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, level, action, actor, status, message, safe_payload, safe_error, ts),
            )
            await db.execute(
                """
                INSERT INTO traces
                  (session_id, trace_type, actor, description, inputs, outputs, reasoning, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    f"proto.{level.lower()}",
                    actor,
                    message,
                    safe_payload,
                    json.dumps({"status": status, "action": action}, ensure_ascii=False),
                    safe_error,
                    ts,
                ),
            )
            await db.commit()
        _console_log(level, f"[{session_id}] {actor}::{action} {status} - {message}", {"payload": payload, "error": error})
    except Exception:
        LOGGER.exception("Failed to persist proto session log")


async def log_proto_exception(
    session_id: str,
    action: str,
    actor: str,
    exc: Exception,
    payload: Any = None,
) -> None:
    """Persist an exception with stack trace in proto mode only."""
    await log_proto(
        session_id=session_id or "global",
        action=action,
        actor=actor,
        message=f"Exception during {action}: {exc}",
        level="ERROR",
        status="failed",
        payload=payload,
        error={
            "type": exc.__class__.__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        },
    )


async def export_session_transcript(session_id: str) -> str:
    """Return a Markdown transcript of a session's chat events."""
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
                lines.append(json.dumps(record, indent=2, ensure_ascii=False))
    return "\n\n".join(lines)


async def export_session_logs(session_id: str) -> list[dict[str, Any]]:
    """Return verbose proto logs for a session."""
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM session_logs WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ) as cursor:
            cols = [column[0] for column in cursor.description]
            records: list[dict[str, Any]] = []
            async for row in cursor:
                records.append({col: row[col] for col in cols})
            return records


async def export_session_replay(session_id: str) -> dict:
    """Return a JSON object containing enough information to replay a session."""
    async with get_db() as db:
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
        traces: list[dict] = []
        async with db.execute(
            "SELECT * FROM traces WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ) as cursor:
            cols = [column[0] for column in cursor.description]
            async for row in cursor:
                record = {col: row[col] for col in cols}
                traces.append(record)
        logs: list[dict] = []
        async with db.execute(
            "SELECT * FROM session_logs WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ) as cursor:
            cols = [column[0] for column in cursor.description]
            async for row in cursor:
                record = {col: row[col] for col in cols}
                logs.append(record)
    return {"events": events, "traces": traces, "logs": logs}
