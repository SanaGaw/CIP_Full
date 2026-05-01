"""Admin routes for CIP."""
from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException

from ..config import get_settings
from ..db import fetch_all, fetch_one

router = APIRouter()


@router.get("/health")
async def health():
    settings = get_settings()
    return {
        "status": "ok",
        "service": "cip-v2",
        "proto_logging_enabled": settings.proto_mode,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/admin/api/config")
async def get_config(settings=Depends(get_settings)):
    data = settings.model_dump()
    data["proto_logging_active"] = bool(settings.proto_mode)
    return data


@router.get("/admin/api/telemetry")
async def get_telemetry():
    sessions = await fetch_one("SELECT COUNT(*) AS count FROM sessions WHERE status = 'active'")
    participants = await fetch_one("SELECT COUNT(*) AS count FROM participants")
    messages = await fetch_one("SELECT COUNT(*) AS count FROM messages")
    traces = await fetch_one("SELECT COUNT(*) AS count FROM traces")
    warnings = await fetch_one("SELECT COUNT(*) AS count FROM session_logs WHERE level = 'WARNING'")
    errors = await fetch_one("SELECT COUNT(*) AS count FROM session_logs WHERE level = 'ERROR'")
    return {
        "active_sessions": int(sessions["count"] if sessions else 0),
        "total_participants": int(participants["count"] if participants else 0),
        "total_messages": int(messages["count"] if messages else 0),
        "messages_per_minute": int(messages["count"] if messages else 0),
        "total_traces": int(traces["count"] if traces else 0),
        "total_proto_logs": int(traces["count"] if traces else 0),
        "total_proto_errors": int(errors["count"] if errors else 0),
        "total_proto_warnings": int(warnings["count"] if warnings else 0),
        "proto_logging_enabled": True,
        "avg_response_time_ms": 0,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/admin/api/sessions")
async def get_sessions(limit: int = 50):
    rows = await fetch_all(
        """
        SELECT s.*,
               (SELECT COUNT(*) FROM participants p WHERE p.session_id = s.id) AS participants_count,
               (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.id) AS messages_count,
               (SELECT COUNT(*) FROM session_logs l WHERE l.session_id = s.id) AS logs_count
        FROM sessions s
        ORDER BY s.created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    return {"sessions": rows, "count": len(rows)}


@router.get("/admin/api/traces")
async def get_traces(session_id: str | None = None, limit: int = 100):
    if session_id:
        rows = await fetch_all("SELECT * FROM traces WHERE session_id = ? ORDER BY id DESC LIMIT ?", (session_id, limit))
    else:
        rows = await fetch_all("SELECT * FROM traces ORDER BY id DESC LIMIT ?", (limit,))
    return {"traces": rows, "count": len(rows)}


@router.get("/admin/api/session-logs")
async def get_session_logs(session_id: str, level: str | None = None, limit: int = 500):
    if level:
        rows = await fetch_all(
            "SELECT * FROM session_logs WHERE session_id = ? AND level = ? ORDER BY id DESC LIMIT ?",
            (session_id, level, limit),
        )
    else:
        rows = await fetch_all("SELECT * FROM session_logs WHERE session_id = ? ORDER BY id DESC LIMIT ?", (session_id, limit))
    return {"logs": rows, "count": len(rows)}


@router.get("/admin/api/transcript")
async def get_transcript(session_id: str):
    messages = await fetch_all(
        """
        SELECT m.*, COALESCE(p.participant_type, m.participant_type) AS participant_type
        FROM messages m
        LEFT JOIN participants p ON m.participant_id = p.id AND m.session_id = p.session_id
        WHERE m.session_id = ?
        ORDER BY m.created_at
        """,
        (session_id,),
    )
    return {"session_id": session_id, "messages": messages, "count": len(messages)}


@router.get("/admin/api/replay")
async def get_replay_data(session_id: str):
    session = await fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = await fetch_all("SELECT * FROM messages WHERE session_id = ? ORDER BY created_at", (session_id,))
    ideas = await fetch_all("SELECT * FROM ideas WHERE session_id = ? ORDER BY created_at", (session_id,))
    clusters = await fetch_all("SELECT * FROM clusters WHERE session_id = ? ORDER BY created_at", (session_id,))
    logs = await fetch_all("SELECT * FROM session_logs WHERE session_id = ? ORDER BY created_at", (session_id,))
    phases = [{"name": name, "active": session.get("current_phase") == name} for name in ["clarification", "ideation", "evaluation", "refinement", "closed"]]
    return {"session_id": session_id, "session": session, "phases": phases, "messages": messages, "ideas": ideas, "clusters": clusters, "logs": logs}


@router.get("/admin/api/report")
async def get_report(session_id: str):
    session = await fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    participants_count = (await fetch_one("SELECT COUNT(*) AS count FROM participants WHERE session_id = ?", (session_id,)) or {}).get("count", 0)
    messages_count = (await fetch_one("SELECT COUNT(*) AS count FROM messages WHERE session_id = ?", (session_id,)) or {}).get("count", 0)
    ideas = await fetch_all("SELECT * FROM ideas WHERE session_id = ?", (session_id,))
    clusters = await fetch_all("SELECT * FROM clusters WHERE session_id = ?", (session_id,))
    injections = await fetch_all("SELECT * FROM injections WHERE session_id = ? ORDER BY id DESC LIMIT 10", (session_id,))
    return {
        "session_id": session_id,
        "status": session.get("status"),
        "participants_count": int(participants_count),
        "messages_count": int(messages_count),
        "total_ideas": len(ideas),
        "total_clusters": len(clusters),
        "recent_injections": injections,
        "report_generated": True,
    }
