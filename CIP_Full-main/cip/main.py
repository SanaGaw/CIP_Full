"""Main entry point for the CIP FastAPI application."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .admin.routes import router as admin_router
from .agents.idea_extractor import extract_ideas, score_quality
from .agents.orchestrator import Orchestrator
from .config import get_settings
from .db import execute, fetch_all, fetch_one, init_db
from .facilitator.routes import router as facilitator_router
from .llm.tier_router import call_with_tier
from .observability import log_event, log_proto, log_proto_exception, log_trace
from .state import connection_manager
from .websocket.manager import ConnectionManager

logger = logging.getLogger(__name__)
settings = get_settings()


def utc_now() -> str:
    return datetime.utcnow().isoformat()


def create_app() -> FastAPI:
    app = FastAPI(title="CIP v2")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup_event() -> None:
        await init_db()
        global connection_manager
        connection_manager = ConnectionManager()
        logger.info("Database initialised and connection manager ready")

    app.include_router(admin_router, prefix="")
    app.include_router(facilitator_router, prefix="")

    app.mount("/static", StaticFiles(directory="cip/static"), name="static")

    def render_html(path: str) -> HTMLResponse:
        file_path = Path(__file__).resolve().parent / path
        return HTMLResponse(file_path.read_text(encoding="utf-8"))

    @app.get("/")
    async def root():
        return render_html("templates/participant/chat.html")

    @app.get("/admin")
    async def admin_dashboard():
        return render_html("templates/admin/dashboard.html")

    @app.get("/facilitator")
    async def facilitator_dashboard():
        return render_html("templates/facilitator/dashboard.html")

    @app.get("/participant")
    async def participant_chat():
        return render_html("templates/participant/chat.html")

    @app.get("/replay")
    async def replay():
        return render_html("templates/replay/session.html")

    @app.websocket("/ws/admin")
    async def admin_ws(ws: WebSocket):
        await connection_manager.connect("admin", ws, audience="admin")
        try:
            while True:
                data = await ws.receive_text()
                await log_trace("global", "admin_ws_message", "admin", "Admin WebSocket payload received", inputs={"raw": data})
        except WebSocketDisconnect:
            connection_manager.disconnect("admin", audience="admin")

    @app.websocket("/ws/facilitator")
    async def facilitator_ws(ws: WebSocket):
        await connection_manager.connect("facilitator", ws, audience="facilitator")
        try:
            while True:
                data = await ws.receive_text()
                await log_trace("global", "facilitator_ws_message", "facilitator", "Facilitator WebSocket payload received", inputs={"raw": data})
        except WebSocketDisconnect:
            connection_manager.disconnect("facilitator", audience="facilitator")

    @app.websocket("/ws/{session_id}/{participant_id}")
    async def participant_session_ws(ws: WebSocket, session_id: str, participant_id: str):
        await connection_manager.connect(participant_id, ws, audience="participant", session_id=session_id)
        await _register_participant(session_id, participant_id, source="websocket_connect")
        await ws.send_json({"type": "system", "text": "Connected", "session_id": session_id})
        await log_proto(session_id, "participant_ws_connected", participant_id, "Participant WebSocket connected", {"participant_id": participant_id})
        try:
            while True:
                raw = await ws.receive_text()
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    payload = {"text": raw}
                text = str(payload.get("text", "")).strip()
                await log_proto(session_id, "participant_ws_payload_received", participant_id, "Participant WebSocket payload received", {"participant_id": participant_id, "payload": payload})
                if not text:
                    await log_proto(session_id, "participant_message_rejected", participant_id, "Participant message ignored because it was empty", {"payload": payload}, level="WARNING", status="rejected")
                    continue
                message_id = await _save_message(session_id, participant_id, text, source="websocket")
                await connection_manager.broadcast_participants(
                    {"type": "message", "session_id": session_id, "participant_id": participant_id, "text": text, "message_id": message_id},
                    session_id=session_id,
                )
                asyncio.create_task(_run_ai_pipeline_after_message(session_id, participant_id, text, message_id))
        except WebSocketDisconnect:
            connection_manager.disconnect(participant_id, audience="participant", session_id=session_id)
            await log_proto(session_id, "participant_ws_disconnected", participant_id, "Participant WebSocket disconnected", {"participant_id": participant_id})

    @app.websocket("/ws/{user_id}")
    async def legacy_ws(ws: WebSocket, user_id: str):
        await connection_manager.connect(user_id, ws, audience="participant")
        try:
            while True:
                data = await ws.receive_text()
                await log_event("default-session", user_id, "message", {"user_id": user_id, "text": data})
                await connection_manager.send_to_user(user_id, {"echo": data})
        except WebSocketDisconnect:
            connection_manager.disconnect(user_id, audience="participant")

    @app.post("/api/session/{session_id}/message")
    async def http_participant_message(session_id: str, body: dict[str, Any]):
        participant_id = str(body.get("participant_id") or "P_HTTP")
        text = str(body.get("text") or "").strip()
        if not text:
            await log_proto(session_id, "participant_message_rejected", participant_id, "HTTP participant message ignored because it was empty", {"participant_id": participant_id}, level="WARNING", status="rejected")
            return {"saved": False, "reason": "empty message"}
        await _register_participant(session_id, participant_id, source="http_message")
        message_id = await _save_message(session_id, participant_id, text, source="http")
        await connection_manager.broadcast_participants(
            {"type": "message", "session_id": session_id, "participant_id": participant_id, "text": text, "message_id": message_id},
            session_id=session_id,
        )
        asyncio.create_task(_run_ai_pipeline_after_message(session_id, participant_id, text, message_id))
        return {"saved": True, "session_id": session_id, "participant_id": participant_id, "text": text, "created_at": utc_now()}

    return app


async def _register_participant(session_id: str, participant_id: str, source: str) -> None:
    ts = utc_now()
    await execute(
        """
        INSERT INTO participants (id, session_id, participant_type, display_name, last_seen_at, created_at)
        VALUES (?, ?, 'participant', ?, ?, ?)
        ON CONFLICT(id, session_id) DO UPDATE SET last_seen_at = excluded.last_seen_at
        """,
        (participant_id, session_id, participant_id, ts, ts),
    )
    await log_proto(session_id, "participant_registered_or_seen", participant_id, "Participant registered or last_seen_at updated", {"participant_id": participant_id, "source": source, "timestamp": ts})


async def _save_message(session_id: str, participant_id: str, text: str, source: str) -> int:
    ts = utc_now()
    await _register_participant(session_id, participant_id, source=f"message:{source}")
    message_id = await execute(
        """
        INSERT INTO messages (session_id, participant_id, text, participant_type, created_at)
        VALUES (?, ?, ?, 'participant', ?)
        """,
        (session_id, participant_id, text, ts),
    )
    await log_event(session_id, participant_id, "message", {"participant_id": participant_id, "text": text, "source": source, "message_id": message_id})
    await log_proto(session_id, "message_saved", participant_id, "Participant message persisted in messages and events tables", {"participant_id": participant_id, "source": source, "text": text, "text_length": len(text), "created_at": ts, "message_id": message_id})
    return message_id


async def _run_ai_pipeline_after_message(session_id: str, participant_id: str, text: str, message_id: int | None = None) -> None:
    """Extract ideas, run the rule-based orchestrator, and periodically call an LLM.

    The important part: this is now called after each valid participant message.
    It is deliberately safe: errors are logged and do not block chat/WebSocket flow.
    """
    try:
        await log_proto(session_id, "ai_pipeline_started", "ai_orchestrator", "AI pipeline triggered after participant message", {"participant_id": participant_id, "message_id": message_id, "text_length": len(text)})

        extracted = extract_ideas(text)
        if not extracted:
            await log_proto(session_id, "ai_no_ideas_extracted", "ai_orchestrator", "No idea extracted from message", {"participant_id": participant_id, "message_id": message_id}, level="WARNING", status="empty")
            return

        for idea_text in extracted:
            quality = await _safe_quality_score(idea_text)
            idea_id = await execute(
                """
                INSERT INTO ideas (session_id, participant_id, text, theme, quality_score, source_message_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, participant_id, idea_text, "auto_extracted", quality, message_id, utc_now()),
            )

            session_state = await _build_session_state(session_id)
            orchestrator = Orchestrator(session_id)
            try:
                result = await orchestrator.classify_idea(
                    {"id": idea_id, "text": idea_text, "participant_id": participant_id, "quality_score": quality},
                    session_state,
                )
                await log_proto(session_id, "orchestrator_classify_completed", "ai_orchestrator", "Rule-based orchestrator classification completed", {"idea_id": idea_id, "quality_score": quality, "result_keys": list(result.keys())})
            except Exception as exc:
                await log_proto_exception(session_id, "orchestrator_classify_failed", "ai_orchestrator", exc, {"idea_id": idea_id, "idea_text": idea_text})

        row = await fetch_one("SELECT COUNT(*) AS count FROM messages WHERE session_id = ?", (session_id,))
        message_count = int(row["count"] if row else 0)
        # LLM throttling: call every 10 valid messages, plus at first message, so you can verify LLM wiring quickly.
        if message_count == 1 or (message_count > 0 and message_count % 10 == 0):
            await _run_llm_cluster_label(session_id, message_count)
        else:
            await log_proto(session_id, "llm_cluster_skipped", "ai_orchestrator", "LLM clustering skipped by throttle", {"message_count": message_count, "rule": "message_count == 1 or divisible by 10"})

    except Exception as exc:
        await log_proto_exception(session_id, "ai_pipeline_failed", "ai_orchestrator", exc, {"participant_id": participant_id, "message_id": message_id, "text": text[:500]})


async def _safe_quality_score(idea_text: str) -> float:
    try:
        return float(score_quality(idea_text))
    except Exception:
        words = len(idea_text.split())
        has_number = any(c.isdigit() for c in idea_text)
        return round(min(1.0, 0.25 + words / 80 + (0.15 if has_number else 0)), 3)


async def _build_session_state(session_id: str) -> dict[str, Any]:
    ideas = await fetch_all("SELECT id, text, theme, quality_score FROM ideas WHERE session_id = ? ORDER BY id DESC LIMIT 80", (session_id,))
    clusters = await fetch_all("SELECT id, label, size FROM clusters WHERE session_id = ? ORDER BY id DESC LIMIT 20", (session_id,))
    participants = await fetch_all("SELECT id, participant_type, display_name FROM participants WHERE session_id = ?", (session_id,))
    session = await fetch_one("SELECT topic, current_phase FROM sessions WHERE id = ?", (session_id,))
    return {
        "ideas": ideas,
        "clusters": clusters,
        "participants": participants,
        "problem_statement": session.get("topic") if session else "",
        "current_phase": session.get("current_phase") if session else "",
    }


async def _run_llm_cluster_label(session_id: str, message_count: int) -> None:
    ideas = await fetch_all("SELECT text, quality_score FROM ideas WHERE session_id = ? ORDER BY id DESC LIMIT 30", (session_id,))
    if not ideas:
        return
    prompt_text = "\n".join([f"- {i['text']} (quality={i.get('quality_score')})" for i in ideas])
    await log_proto(session_id, "llm_cluster_call_started", "ai_orchestrator", "Calling LLM for cluster labels", {"message_count": message_count, "ideas_sent": len(ideas), "task_id": "orch.cluster_label"})
    llm_result = await call_with_tier(
        task_id="orch.cluster_label",
        system="You are a collective intelligence facilitator. Group participant ideas into clear clusters and give concise labels.",
        messages=[{"role": "user", "content": f"Cluster these ideas and return concise cluster labels with one short reason each:\n{prompt_text}"}],
        max_tokens=500,
        temperature=0.2,
        session_id=session_id,
    )
    label_text = (llm_result.get("text") or "LLM returned no label; check provider/API key traces.").strip()
    await execute(
        "INSERT INTO clusters (session_id, label, size, payload, created_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, label_text[:300], len(ideas), json.dumps(llm_result, ensure_ascii=False, default=str), utc_now()),
    )
    await log_proto(
        session_id,
        "llm_cluster_call_completed",
        "ai_orchestrator",
        "LLM clustering completed or fallback returned",
        {
            "message_count": message_count,
            "provider": llm_result.get("provider"),
            "model": llm_result.get("model"),
            "input_tokens": llm_result.get("input_tokens"),
            "output_tokens": llm_result.get("output_tokens"),
        },
    )


app = create_app()
