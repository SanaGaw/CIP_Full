"""Main entry point for the CIP FastAPI application."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .admin.routes import router as admin_router
from .config import get_settings
from .db import execute, init_db
from .facilitator.routes import router as facilitator_router
from .observability import log_event
from .websocket.manager import ConnectionManager

settings = get_settings()
connection_manager = ConnectionManager()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
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

    app.include_router(admin_router, prefix="")
    app.include_router(facilitator_router, prefix="")
    app.mount("/static", StaticFiles(directory="cip/static"), name="static")

    def render_html(path: str) -> HTMLResponse:
        file_path = Path(__file__).resolve().parent / path
        return HTMLResponse(file_path.read_text(encoding="utf-8"))

    @app.get("/")
    async def root():
        return {
            "message": "CIP v2 API",
            "interfaces": {
                "admin": "/admin",
                "facilitator": "/facilitator",
                "participant": "/participant?session_id=YOUR_SESSION_ID",
                "replay": "/replay?session_id=YOUR_SESSION_ID",
            },
        }

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
    async def replay_viewer():
        return render_html("templates/replay/session.html")

    @app.post("/api/session/{session_id}/message")
    async def post_message(session_id: str, payload: dict[str, Any]):
        """HTTP fallback to save a participant message."""
        participant_id = str(payload.get("participant_id") or "anonymous")
        text = str(payload.get("text") or "").strip()
        if not text:
            return {"saved": False, "reason": "empty message"}
        now = datetime.utcnow().isoformat()
        await _save_message(session_id, participant_id, text, now)
        return {"saved": True, "session_id": session_id, "participant_id": participant_id, "text": text, "created_at": now}

    @app.websocket("/ws/{user_id}")
    async def websocket_endpoint(ws: WebSocket, user_id: str):
        """Compatibility WebSocket endpoint used by admin/facilitator pages."""
        audience = "admin" if user_id == "admin" else "facilitator" if user_id == "facilitator" else "participant"
        await connection_manager.connect(user_id, ws, audience=audience)
        try:
            while True:
                data = await ws.receive_text()
                await connection_manager.send_to_user(user_id, {"type": "echo", "text": data})
        except WebSocketDisconnect:
            connection_manager.disconnect(user_id, audience=audience)

    @app.websocket("/ws/{session_id}/{participant_id}")
    async def participant_websocket(ws: WebSocket, session_id: str, participant_id: str):
        """Participant WebSocket endpoint for live chat."""
        connection_key = f"{session_id}:{participant_id}"
        await connection_manager.connect_session(session_id, participant_id, ws)
        await _register_participant(session_id, participant_id)
        try:
            await ws.send_json({"type": "system", "text": "Connected", "session_id": session_id})
            while True:
                data = await ws.receive_json()
                text = str(data.get("text") or "").strip()
                if not text:
                    continue
                now = datetime.utcnow().isoformat()
                await _save_message(session_id, participant_id, text, now)
                message = {
                    "type": "message",
                    "session_id": session_id,
                    "participant_id": participant_id,
                    "text": text,
                    "timestamp": now,
                    "created_at": now,
                }
                await connection_manager.broadcast_session(session_id, message)
                await connection_manager.broadcast_admin({"type": "new_message", **message})
                await connection_manager.broadcast_facilitator({"type": "session_update", "session_id": session_id})
        except WebSocketDisconnect:
            connection_manager.disconnect_session(session_id, participant_id)

    return app


async def _register_participant(session_id: str, participant_id: str) -> None:
    now = datetime.utcnow().isoformat()
    await execute(
        """
        INSERT OR IGNORE INTO sessions (id, status, current_phase, topic, config, duration_seconds, created_at, updated_at)
        VALUES (?, 'active', 'clarification', 'Ad-hoc session', '{}', 0, ?, ?)
        """,
        (session_id, now, now),
    )
    await execute(
        """
        INSERT OR REPLACE INTO participants
          (id, session_id, participant_type, display_name, created_at, last_seen_at)
        VALUES (
          ?, ?, 'participant', ?,
          COALESCE((SELECT created_at FROM participants WHERE id = ? AND session_id = ?), ?), ?
        )
        """,
        (participant_id, session_id, participant_id, participant_id, session_id, now, now),
    )


async def _save_message(session_id: str, participant_id: str, text: str, created_at: str) -> None:
    await _register_participant(session_id, participant_id)
    await execute(
        "INSERT INTO messages (session_id, participant_id, text, created_at) VALUES (?, ?, ?, ?)",
        (session_id, participant_id, text, created_at),
    )
    await log_event(session_id, participant_id, "message", {"session_id": session_id, "user_id": participant_id, "text": text})


app = create_app()
