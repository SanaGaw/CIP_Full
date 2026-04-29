"""Facilitator routes for CIP.

The facilitator API manages pilot sessions: start, phase changes, challenge
prompts, injected content and state monitoring.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from ..db import execute, fetch_all, fetch_one
from ..observability import log_event, log_proto, log_proto_exception

router = APIRouter()

VALID_PHASES = ["clarification", "ideation", "evaluation", "refinement", "closed"]


@router.post("/facilitator/api/session/start")
async def start_session(config: dict[str, Any] | None = None):
    """Start a new facilitation session."""
    config = config or {}
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    topic = str(config.get("topic") or "Untitled collective intelligence session")

    try:
        await execute(
            """
            INSERT INTO sessions (id, status, current_phase, topic, config, duration_seconds, created_at, updated_at)
            VALUES (?, 'active', 'clarification', ?, ?, 0, ?, ?)
            """,
            (session_id, topic, json.dumps(config), now, now),
        )
        await execute(
            "INSERT OR REPLACE INTO session_configs (session_id, config, created_at) VALUES (?, ?, ?)",
            (session_id, json.dumps(config), now),
        )
        await log_event(session_id, "facilitator", "session_started", {"session_id": session_id, "topic": topic, "config": config})
        await log_proto(
            session_id=session_id,
            action="session_started",
            actor="facilitator",
            message="Facilitator started a new session",
            payload={"topic": topic, "config": config, "created_at": now},
        )
        return {
            "session_id": session_id,
            "status": "started",
            "phase": "clarification",
            "topic": topic,
            "participant_url": f"/participant?session_id={session_id}",
            "replay_url": f"/replay?session_id={session_id}",
        }
    except Exception as exc:
        await log_proto_exception(session_id, "session_start", "facilitator", exc, {"topic": topic, "config": config})
        raise


@router.post("/facilitator/api/session/phase")
async def advance_phase(session_id: str, phase: str):
    """Advance the session to a new phase."""
    if phase not in VALID_PHASES:
        await log_proto(
            session_id=session_id,
            action="phase_change_rejected",
            actor="facilitator",
            level="WARNING",
            status="rejected",
            message="Invalid phase requested",
            payload={"requested_phase": phase, "valid_phases": VALID_PHASES},
        )
        raise HTTPException(status_code=400, detail=f"Invalid phase. Must be one of: {VALID_PHASES}")

    session = await fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))
    if not session:
        await log_proto(
            session_id=session_id,
            action="phase_change_failed",
            actor="facilitator",
            level="ERROR",
            status="failed",
            message="Session not found while changing phase",
            payload={"requested_phase": phase},
        )
        raise HTTPException(status_code=404, detail="Session not found")

    old_phase = session.get("current_phase")
    status = "closed" if phase == "closed" else "active"
    now = datetime.utcnow().isoformat()
    await execute(
        "UPDATE sessions SET current_phase = ?, status = ?, updated_at = ? WHERE id = ?",
        (phase, status, now, session_id),
    )
    await log_event(session_id, "facilitator", "phase_changed", {"old_phase": old_phase, "new_phase": phase, "status": status})
    await log_proto(
        session_id=session_id,
        action="phase_changed",
        actor="facilitator",
        message=f"Session phase changed from {old_phase} to {phase}",
        payload={"old_phase": old_phase, "new_phase": phase, "status": status, "updated_at": now},
    )
    return {"session_id": session_id, "phase": phase, "status": "updated"}


@router.post("/facilitator/api/session/devil")
async def trigger_devil(session_id: str, phase: str = "clarification"):
    """Trigger a devil's advocate challenge for a session phase."""
    session = await fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))
    if not session:
        await log_proto(
            session_id=session_id,
            action="devil_trigger_failed",
            actor="facilitator",
            level="ERROR",
            status="failed",
            message="Session not found while triggering devil's advocate",
            payload={"phase": phase},
        )
        raise HTTPException(status_code=404, detail="Session not found")

    challenge_bank = {
        "clarification": [
            "What problem are we assuming exists, and what evidence proves it?",
            "Who is affected by this problem but is not represented in the discussion?",
            "What would make this problem statement too narrow or too broad?",
        ],
        "ideation": [
            "What idea would we reject too quickly because it looks unrealistic?",
            "Which silent constraint could block the strongest proposal?",
            "What alternative would a customer, operator or field user suggest?",
        ],
        "evaluation": [
            "Which option wins only because it is familiar?",
            "What risk would appear after 3 months of deployment?",
            "What criterion is missing from the current evaluation?",
        ],
        "refinement": [
            "What is the smallest pilot that can falsify this solution?",
            "Which responsibility is still ambiguous?",
            "What must be measured from day one?",
        ],
    }
    challenges = challenge_bank.get(phase, challenge_bank["clarification"])
    now = datetime.utcnow().isoformat()

    await execute(
        """
        INSERT INTO injections (session_id, content, content_type, created_at)
        VALUES (?, ?, 'devil_challenge', ?)
        """,
        (session_id, json.dumps(challenges), now),
    )
    await log_event(session_id, "facilitator", "devil_challenge", {"phase": phase, "challenges": challenges})
    await log_proto(
        session_id=session_id,
        action="devil_challenge_created",
        actor="facilitator",
        message="Devil's advocate challenge saved as injection",
        payload={"phase": phase, "challenges": challenges, "created_at": now},
    )
    return {"session_id": session_id, "devil_triggered": True, "phase": phase, "challenges": challenges}


@router.post("/facilitator/api/session/inject")
async def inject_content(session_id: str, content: str, content_type: str = "prompt"):
    """Inject facilitator content into the session."""
    session = await fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))
    if not session:
        await log_proto(
            session_id=session_id,
            action="content_injection_failed",
            actor="facilitator",
            level="ERROR",
            status="failed",
            message="Session not found while saving injection",
            payload={"content_type": content_type},
        )
        raise HTTPException(status_code=404, detail="Session not found")
    if not content.strip():
        await log_proto(
            session_id=session_id,
            action="content_injection_rejected",
            actor="facilitator",
            level="WARNING",
            status="rejected",
            message="Injection rejected because content was empty",
            payload={"content_type": content_type},
        )
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    now = datetime.utcnow().isoformat()
    clean_content = content.strip()
    await execute(
        "INSERT INTO injections (session_id, content, content_type, created_at) VALUES (?, ?, ?, ?)",
        (session_id, clean_content, content_type, now),
    )
    await log_event(session_id, "facilitator", "content_injected", {"content_type": content_type, "content": clean_content})
    await log_proto(
        session_id=session_id,
        action="content_injected",
        actor="facilitator",
        message="Facilitator content injection saved",
        payload={"content_type": content_type, "content": clean_content, "created_at": now},
    )
    return {"session_id": session_id, "injected": True, "content_type": content_type, "content": clean_content}


@router.get("/facilitator/api/session/state")
async def get_session_state(session_id: str):
    """Get the current state of a facilitation session."""
    session = await fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))
    if not session:
        await log_proto(
            session_id=session_id,
            action="session_state_failed",
            actor="facilitator",
            level="ERROR",
            status="failed",
            message="Session not found while loading state",
        )
        raise HTTPException(status_code=404, detail="Session not found")

    ideas = await fetch_one("SELECT COUNT(*) AS count FROM ideas WHERE session_id = ?", (session_id,))
    participants = await fetch_one("SELECT COUNT(*) AS count FROM participants WHERE session_id = ?", (session_id,))
    messages = await fetch_one("SELECT COUNT(*) AS count FROM messages WHERE session_id = ?", (session_id,))
    injections = await fetch_all(
        "SELECT * FROM injections WHERE session_id = ? ORDER BY created_at DESC LIMIT 8",
        (session_id,),
    )

    result = {
        "session_id": session_id,
        "topic": session.get("topic"),
        "status": session.get("status"),
        "phase": session.get("current_phase"),
        "created_at": session.get("created_at"),
        "ideas_count": ideas["count"] if ideas else 0,
        "participants_count": participants["count"] if participants else 0,
        "messages_count": messages["count"] if messages else 0,
        "recent_injections": injections,
    }
    await log_proto(
        session_id=session_id,
        action="session_state_loaded",
        actor="facilitator",
        message="Facilitator loaded live session state",
        payload={k: v for k, v in result.items() if k != "recent_injections"},
    )
    return result
