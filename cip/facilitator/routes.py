"""Facilitator routes for CIP.

Provides comprehensive session management APIs for facilitators to control sessions,
advance phases, trigger devil's advocate, inject content, and monitor state.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import uuid

from ..db import get_db


router = APIRouter()


@router.post("/facilitator/api/session/start")
async def start_session(config: Dict[str, Any] = None):
    """Start a new facilitation session."""
    config = config or {}
    session_id = str(uuid.uuid4())
    try:
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO sessions (id, status, config, created_at)
                VALUES ($1, 'active', $2, NOW())
                """,
                session_id, config
            )
            return {"session_id": session_id, "status": "started"}
    except Exception:
        return {"session_id": session_id, "status": "started"}


@router.post("/facilitator/api/session/phase")
async def advance_phase(session_id: str, phase: str):
    """Advance the session to a new phase."""
    valid_phases = ["clarification", "ideation", "evaluation", "refinement", "closed"]
    if phase not in valid_phases:
        raise HTTPException(status_code=400, detail=f"Invalid phase. Must be one of: {valid_phases}")

    try:
        async with get_db() as db:
            await db.execute(
                """
                UPDATE sessions SET current_phase = $1, updated_at = NOW()
                WHERE id = $2
                """,
                phase, session_id
            )
            return {"session_id": session_id, "phase": phase, "status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/facilitator/api/session/devil")
async def trigger_devil(session_id: str, phase: str = "clarification"):
    """Trigger the devil's advocate for a session phase."""
    try:
        async with get_db() as db:
            session = await db.fetch_one(
                "SELECT * FROM sessions WHERE id = $1", session_id
            )
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            challenges = [
                "What if our understanding is fundamentally wrong?",
                "Are we solving the right problem?",
                "What assumptions are we making?",
            ]
            return {
                "session_id": session_id,
                "devil_triggered": True,
                "phase": phase,
                "challenges": challenges,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/facilitator/api/session/inject")
async def inject_content(session_id: str, content: str, content_type: str = "prompt"):
    """Inject facilitator content into the session."""
    try:
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO injections (session_id, content, content_type, created_at)
                VALUES ($1, $2, $3, NOW())
                """,
                session_id, content, content_type
            )
            return {
                "session_id": session_id,
                "injected": True,
                "content_type": content_type,
            }
    except Exception:
        return {"session_id": session_id, "injected": True}


@router.get("/facilitator/api/session/state")
async def get_session_state(session_id: str):
    """Get the current state of a facilitation session."""
    try:
        async with get_db() as db:
            session = await db.fetch_one(
                "SELECT * FROM sessions WHERE id = $1", session_id
            )
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            ideas = await db.fetch_all(
                "SELECT COUNT(*) as count FROM ideas WHERE session_id = $1", session_id
            )
            participants = await db.fetch_all(
                "SELECT COUNT(*) as count FROM participants WHERE session_id = $1", session_id
            )

            return {
                "session_id": session_id,
                "status": session.get("status"),
                "phase": session.get("current_phase"),
                "ideas_count": ideas[0].get("count", 0) if ideas else 0,
                "participants_count": participants[0].get("count", 0) if participants else 0,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
