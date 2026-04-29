"""Admin routes for CIP.

These endpoints power the operator dashboard, replay viewer and post-session
inspection tools. They are intentionally lightweight and SQLite-friendly.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..config import get_settings
from ..db import fetch_all, fetch_one
from ..observability import log_proto, proto_logging_enabled

router = APIRouter()


def _mask_secret(value: Any) -> str:
    if not value:
        return "not configured"
    text = str(value)
    if len(text) <= 6:
        return "configured"
    return f"{text[:3]}...{text[-3:]}"


@router.get("/health")
async def health():
    """Simple health check endpoint."""
    return {
        "status": "ok",
        "service": "cip-v2",
        "proto_logging_enabled": proto_logging_enabled(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/admin/api/config")
async def get_config(settings=Depends(get_settings)):
    """Return a safe view of the current configuration values."""
    raw = settings.model_dump()
    safe: dict[str, Any] = {}
    for key, value in raw.items():
        if "password" in key or key.endswith("api_key"):
            safe[key] = _mask_secret(value)
        else:
            safe[key] = value
    safe["proto_logging_active"] = proto_logging_enabled()
    return safe


@router.get("/admin/api/sessions")
async def list_sessions(limit: int = 50):
    """Return recent sessions for dropdowns and quick access."""
    rows = await fetch_all(
        """
        SELECT
          s.id,
          s.status,
          s.current_phase,
          s.topic,
          s.created_at,
          s.updated_at,
          COUNT(DISTINCT p.id) AS participants_count,
          COUNT(DISTINCT m.id) AS messages_count,
          COUNT(DISTINCT l.id) AS logs_count
        FROM sessions s
        LEFT JOIN participants p ON p.session_id = s.id
        LEFT JOIN messages m ON m.session_id = s.id
        LEFT JOIN session_logs l ON l.session_id = s.id
        GROUP BY s.id
        ORDER BY s.created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    return {"sessions": rows, "count": len(rows)}


@router.get("/admin/api/telemetry")
async def get_telemetry():
    """Return live-ish telemetry from the SQLite tables."""
    since = (datetime.utcnow() - timedelta(minutes=1)).isoformat()
    active = await fetch_one("SELECT COUNT(*) AS count FROM sessions WHERE status = 'active'")
    participants = await fetch_one("SELECT COUNT(*) AS count FROM participants")
    messages = await fetch_one("SELECT COUNT(*) AS count FROM messages")
    recent_messages = await fetch_one("SELECT COUNT(*) AS count FROM messages WHERE created_at >= ?", (since,))
    traces = await fetch_one("SELECT COUNT(*) AS count FROM traces")
    logs = await fetch_one("SELECT COUNT(*) AS count FROM session_logs")
    errors = await fetch_one("SELECT COUNT(*) AS count FROM session_logs WHERE level = 'ERROR'")
    warnings = await fetch_one("SELECT COUNT(*) AS count FROM session_logs WHERE level = 'WARNING'")
    return {
        "active_sessions": active["count"] if active else 0,
        "total_participants": participants["count"] if participants else 0,
        "total_messages": messages["count"] if messages else 0,
        "messages_per_minute": recent_messages["count"] if recent_messages else 0,
        "total_traces": traces["count"] if traces else 0,
        "total_proto_logs": logs["count"] if logs else 0,
        "total_proto_errors": errors["count"] if errors else 0,
        "total_proto_warnings": warnings["count"] if warnings else 0,
        "proto_logging_enabled": proto_logging_enabled(),
        "avg_response_time_ms": 0,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/admin/api/traces")
async def get_traces(session_id: str | None = None, limit: int = 100):
    """Return trace logs for sessions."""
    if session_id:
        traces = await fetch_all(
            "SELECT * FROM traces WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit),
        )
        await log_proto(
            session_id=session_id,
            action="admin_traces_loaded",
            actor="admin",
            message="Admin loaded traces for selected session",
            payload={"limit": limit, "count": len(traces)},
        )
    else:
        traces = await fetch_all("SELECT * FROM traces ORDER BY created_at DESC LIMIT ?", (limit,))
    return {"traces": traces, "count": len(traces)}


@router.get("/admin/api/session-logs")
async def get_session_logs(session_id: str | None = None, limit: int = 200, level: str | None = None):
    """Return verbose proto logs saved in session_logs.

    These records exist only when PROTO_MODE=True and PROTO_VERBOSE_LOGGING=True.
    """
    params: list[Any] = []
    where: list[str] = []
    if session_id:
        where.append("session_id = ?")
        params.append(session_id)
    if level:
        where.append("level = ?")
        params.append(level.upper())
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    params.append(limit)
    logs = await fetch_all(
        f"SELECT * FROM session_logs {where_sql} ORDER BY created_at DESC LIMIT ?",
        tuple(params),
    )
    if session_id:
        await log_proto(
            session_id=session_id,
            action="admin_proto_logs_loaded",
            actor="admin",
            message="Admin loaded verbose proto logs for selected session",
            payload={"limit": limit, "level": level, "count": len(logs)},
        )
    return {"logs": logs, "count": len(logs), "proto_logging_enabled": proto_logging_enabled()}


@router.get("/admin/api/report")
async def get_report(session_id: str):
    """Generate a compact JSON report for a session."""
    session = await fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))
    if not session:
        await log_proto(
            session_id=session_id,
            action="admin_report_failed",
            actor="admin",
            level="ERROR",
            status="failed",
            message="Admin report requested for missing session",
        )
        raise HTTPException(status_code=404, detail="Session not found")

    ideas = await fetch_all("SELECT * FROM ideas WHERE session_id = ? ORDER BY created_at", (session_id,))
    clusters = await fetch_all("SELECT * FROM clusters WHERE session_id = ? ORDER BY created_at", (session_id,))
    participants = await fetch_one("SELECT COUNT(*) AS count FROM participants WHERE session_id = ?", (session_id,))
    messages = await fetch_one("SELECT COUNT(*) AS count FROM messages WHERE session_id = ?", (session_id,))
    injections = await fetch_all("SELECT * FROM injections WHERE session_id = ? ORDER BY created_at DESC", (session_id,))
    logs = await fetch_one("SELECT COUNT(*) AS count FROM session_logs WHERE session_id = ?", (session_id,))
    errors = await fetch_one("SELECT COUNT(*) AS count FROM session_logs WHERE session_id = ? AND level = 'ERROR'", (session_id,))
    warnings = await fetch_one("SELECT COUNT(*) AS count FROM session_logs WHERE session_id = ? AND level = 'WARNING'", (session_id,))

    report = {
        "session_id": session_id,
        "topic": session.get("topic"),
        "status": session.get("status"),
        "phase": session.get("current_phase"),
        "created_at": session.get("created_at"),
        "participants_count": participants["count"] if participants else 0,
        "messages_count": messages["count"] if messages else 0,
        "total_ideas": len(ideas),
        "total_clusters": len(clusters),
        "recent_injections": injections[:5],
        "proto_logs_count": logs["count"] if logs else 0,
        "proto_errors_count": errors["count"] if errors else 0,
        "proto_warnings_count": warnings["count"] if warnings else 0,
        "proto_logging_enabled": proto_logging_enabled(),
        "report_generated": True,
    }
    await log_proto(
        session_id=session_id,
        action="admin_report_loaded",
        actor="admin",
        message="Admin loaded session report",
        payload={k: v for k, v in report.items() if k != "recent_injections"},
    )
    return report


@router.get("/admin/api/transcript")
async def get_transcript(session_id: str):
    """Return the full transcript for a session."""
    session = await fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))
    if not session:
        await log_proto(
            session_id=session_id,
            action="admin_transcript_failed",
            actor="admin",
            level="ERROR",
            status="failed",
            message="Transcript requested for missing session",
        )
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await fetch_all(
        """
        SELECT m.*, COALESCE(p.participant_type, 'participant') AS participant_type
        FROM messages m
        LEFT JOIN participants p
          ON m.participant_id = p.id AND m.session_id = p.session_id
        WHERE m.session_id = ?
        ORDER BY m.created_at
        """,
        (session_id,),
    )
    await log_proto(
        session_id=session_id,
        action="admin_transcript_loaded",
        actor="admin",
        message="Admin loaded transcript",
        payload={"messages_count": len(messages)},
    )
    return {"session_id": session_id, "messages": messages, "count": len(messages)}


@router.get("/admin/api/replay")
async def get_replay_data(session_id: str):
    """Return data suitable for the replay viewer."""
    session = await fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))
    if not session:
        await log_proto(
            session_id=session_id,
            action="admin_replay_failed",
            actor="admin",
            level="ERROR",
            status="failed",
            message="Replay requested for missing session",
        )
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await fetch_all(
        """
        SELECT m.*, COALESCE(p.participant_type, 'participant') AS participant_type
        FROM messages m
        LEFT JOIN participants p
          ON m.participant_id = p.id AND m.session_id = p.session_id
        WHERE m.session_id = ?
        ORDER BY m.created_at
        """,
        (session_id,),
    )
    ideas = await fetch_all("SELECT * FROM ideas WHERE session_id = ? ORDER BY created_at", (session_id,))
    traces = await fetch_all("SELECT * FROM traces WHERE session_id = ? ORDER BY created_at", (session_id,))
    logs = await fetch_all("SELECT * FROM session_logs WHERE session_id = ? ORDER BY created_at", (session_id,))

    phases = [
        {"name": "clarification", "active": session.get("current_phase") == "clarification"},
        {"name": "ideation", "active": session.get("current_phase") == "ideation"},
        {"name": "evaluation", "active": session.get("current_phase") == "evaluation"},
        {"name": "refinement", "active": session.get("current_phase") == "refinement"},
        {"name": "closed", "active": session.get("current_phase") == "closed"},
    ]

    duration_seconds = 0
    if messages:
        start = datetime.fromisoformat(messages[0]["created_at"])
        end = datetime.fromisoformat(messages[-1]["created_at"])
        duration_seconds = max(1, int((end - start).total_seconds()))

    await log_proto(
        session_id=session_id,
        action="admin_replay_loaded",
        actor="admin",
        message="Admin/replay viewer loaded replay data",
        payload={"messages_count": len(messages), "ideas_count": len(ideas), "traces_count": len(traces), "logs_count": len(logs)},
    )
    return {
        "session_id": session_id,
        "session": session,
        "phases": phases,
        "messages": messages,
        "ideas": ideas,
        "traces": traces,
        "logs": logs,
        "duration_seconds": duration_seconds,
        "proto_logging_enabled": proto_logging_enabled(),
    }
