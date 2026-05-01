"""Facilitator routes for CIP."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..db import execute, fetch_all, fetch_one
from ..observability import log_proto

router = APIRouter()


def now() -> str:
    return datetime.utcnow().isoformat()


DEVIL_CHALLENGES = {
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


@router.post("/facilitator/api/session/start")
async def start_session(config: Dict[str, Any] | None = None):
    config = config or {}
    session_id = str(uuid.uuid4())
    topic = config.get("topic") or "Untitled session"
    ts = now()
    await execute(
        """
        INSERT INTO sessions (id, status, current_phase, topic, config, created_at, updated_at)
        VALUES (?, 'active', 'clarification', ?, ?, ?, ?)
        """,
        (session_id, topic, json.dumps(config, ensure_ascii=False, default=str), ts, ts),
    )
    await execute(
        "INSERT OR REPLACE INTO session_configs (session_id, config, created_at) VALUES (?, ?, ?)",
        (session_id, json.dumps(config, ensure_ascii=False, default=str), ts),
    )
    await log_proto(session_id, "session_started", "facilitator", "Facilitator started a new session", {"topic": topic, "config": config})
    return {
        "session_id": session_id,
        "status": "started",
        "phase": "clarification",
        "topic": topic,
        "participant_url": f"/participant?session_id={session_id}",
        "replay_url": f"/replay?session_id={session_id}",
    }


@router.post("/facilitator/api/session/phase")
async def advance_phase(session_id: str, phase: str):
    valid_phases = ["clarification", "ideation", "evaluation", "refinement", "closed"]
    if phase not in valid_phases:
        raise HTTPException(status_code=400, detail=f"Invalid phase. Must be one of: {valid_phases}")
    session = await fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    status = "closed" if phase == "closed" else "active"
    await execute(
        "UPDATE sessions SET current_phase = ?, status = ?, updated_at = ? WHERE id = ?",
        (phase, status, now(), session_id),
    )
    await log_proto(session_id, "phase_changed", "facilitator", f"Session phase changed to {phase}", {"phase": phase})
    return {"session_id": session_id, "phase": phase, "status": "updated"}


@router.post("/facilitator/api/session/devil")
async def trigger_devil(session_id: str, phase: str = "clarification"):
    session = await fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    challenges = DEVIL_CHALLENGES.get(phase, DEVIL_CHALLENGES["evaluation"])
    await log_proto(session_id, "devil_advocate_triggered", "facilitator", f"Devil advocate triggered in {phase}", {"phase": phase, "challenges": challenges})
    return {"session_id": session_id, "devil_triggered": True, "phase": phase, "challenges": challenges}


@router.post("/facilitator/api/session/inject")
async def inject_content(session_id: str, content: str, content_type: str = "prompt"):
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    ts = now()
    await execute(
        "INSERT INTO injections (session_id, content, content_type, created_at) VALUES (?, ?, ?, ?)",
        (session_id, content.strip(), content_type, ts),
    )
    await log_proto(session_id, "content_injected", "facilitator", "Facilitator injected content", {"content_type": content_type, "content": content.strip()})
    return {"session_id": session_id, "injected": True, "content_type": content_type, "content": content.strip()}


@router.get("/facilitator/api/session/state")
async def get_session_state(session_id: str):
    session = await fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    ideas = await fetch_one("SELECT COUNT(*) AS count FROM ideas WHERE session_id = ?", (session_id,))
    participants = await fetch_one("SELECT COUNT(*) AS count FROM participants WHERE session_id = ?", (session_id,))
    messages = await fetch_one("SELECT COUNT(*) AS count FROM messages WHERE session_id = ?", (session_id,))
    recent_injections = await fetch_all(
        "SELECT content_type, content, created_at FROM injections WHERE session_id = ? ORDER BY id DESC LIMIT 5",
        (session_id,),
    )
    return {
        "session_id": session_id,
        "topic": session.get("topic"),
        "status": session.get("status"),
        "phase": session.get("current_phase"),
        "created_at": session.get("created_at"),
        "ideas_count": int(ideas["count"] if ideas else 0),
        "participants_count": int(participants["count"] if participants else 0),
        "messages_count": int(messages["count"] if messages else 0),
        "recent_injections": recent_injections,
    }
