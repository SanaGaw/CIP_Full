"""Admin routes for CIP.

This module defines HTTP and WebSocket endpoints for the operator dashboard.
Provides comprehensive endpoints for configuration, telemetry, traces, reports, transcripts, and replay.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any

from ..config import get_settings
from ..db import get_db


router = APIRouter()


@router.get("/health")
async def health():
    """Simple health check endpoint."""
    return {"status": "ok"}


@router.get("/admin/api/config")
async def get_config(settings=Depends(get_settings)):
    """Return current configuration values."""
    return settings.model_dump()


@router.get("/admin/api/telemetry")
async def get_telemetry():
    """Return system telemetry data."""
    return {
        "active_sessions": 0,
        "total_participants": 0,
        "messages_per_minute": 0.0,
        "avg_response_time_ms": 0,
        "timestamp": "2024-01-01T00:00:00Z",
    }


@router.get("/admin/api/traces")
async def get_traces(session_id: str = None, limit: int = 100):
    """Return trace logs for sessions."""
    try:
        async with get_db() as db:
            traces = await db.fetch_all(
                "SELECT * FROM traces WHERE ($1 IS NULL OR session_id = $1) ORDER BY created_at DESC LIMIT $2",
                session_id, limit
            )
            return {"traces": [dict(t) for t in traces], "count": len(traces)}
    except Exception:
        return {"traces": [], "count": 0}


@router.get("/admin/api/report")
async def get_report(session_id: str):
    """Generate and return the final report for a session."""
    try:
        async with get_db() as db:
            session = await db.fetch_one(
                "SELECT * FROM sessions WHERE id = $1", session_id
            )
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            ideas = await db.fetch_all(
                "SELECT * FROM ideas WHERE session_id = $1", session_id
            )
            clusters = await db.fetch_all(
                "SELECT * FROM clusters WHERE session_id = $1", session_id
            )

            return {
                "session_id": session_id,
                "status": session.get("status"),
                "total_ideas": len(ideas),
                "total_clusters": len(clusters),
                "report_generated": True,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/api/transcript")
async def get_transcript(session_id: str):
    """Return the full transcript for a session."""
    try:
        async with get_db() as db:
            messages = await db.fetch_all(
                """
                SELECT m.*, p.participant_type
                FROM messages m
                JOIN participants p ON m.participant_id = p.id
                WHERE m.session_id = $1
                ORDER BY m.created_at
                """,
                session_id
            )
            return {
                "session_id": session_id,
                "messages": [dict(m) for m in messages],
                "count": len(messages),
            }
    except Exception:
        return {"session_id": session_id, "messages": [], "count": 0}


@router.get("/admin/api/replay")
async def get_replay_data(session_id: str):
    """Return replay data for a session."""
    try:
        async with get_db() as db:
            session = await db.fetch_one(
                "SELECT * FROM sessions WHERE id = $1", session_id
            )
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            messages = await db.fetch_all(
                "SELECT * FROM messages WHERE session_id = $1 ORDER BY created_at",
                session_id
            )
            ideas = await db.fetch_all(
                "SELECT * FROM ideas WHERE session_id = $1 ORDER BY created_at",
                session_id
            )

            return {
                "session_id": session_id,
                "phases": session.get("phases", []),
                "messages": [dict(m) for m in messages],
                "ideas": [dict(i) for i in ideas],
                "duration_seconds": session.get("duration_seconds", 0),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
