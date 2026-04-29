"""Main entry point for the CIP FastAPI application."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .admin.routes import router as admin_router
from .config import get_settings
from .db import execute, init_db
from .facilitator.routes import router as facilitator_router
from .observability import log_event, log_proto, log_proto_exception, proto_logging_enabled
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

    @app.middleware("http")
    async def proto_request_logger(request: Request, call_next):
        """Log HTTP requests for a session only when prototype logging is enabled."""
        start = perf_counter()
        session_id = request.query_params.get("session_id") or "global"
        path = request.url.path
        try:
            response = await call_next(request)
            if proto_logging_enabled() and not path.startswith("/static"):
                duration_ms = round((perf_counter() - start) * 1000, 2)
                level = "WARNING" if response.status_code >= 400 else "INFO"
                await log_proto(
                    session_id=session_id,
                    action="http_request",
                    actor="http",
                    level=level,
                    status="ok" if response.status_code < 400 else "warning",
                    message=f"{request.method} {path} returned {response.status_code}",
                    payload={
                        "method": request.method,
                        "path": path,
                        "query": dict(request.query_params),
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                    },
                )
            return response
        except Exception as exc:
            await log_proto_exception(
                session_id=session_id,
                action="http_request",
                actor="http",
                exc=exc,
                payload={"method": request.method, "path": path, "query": dict(request.query_params)},
            )
            raise

    @app.on_event("startup")
    async def startup_event() -> None:
        await init_db()
        await log_proto(
            session_id="global",
            action="app_startup",
            actor="system",
            message="Application started and database initialized",
            payload={
                "proto_mode": settings.proto_mode,
                "proto_verbose_logging": settings.proto_verbose_logging,
                "pilot_mode": settings.pilot_mode,
                "dev_mode": settings.dev_mode,
                "log_level": settings.log_level,
            },
        )

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
            "proto_logging_enabled": proto_logging_enabled(),
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
            await log_proto(
                session_id=session_id,
                action="http_message_rejected",
                actor=participant_id,
                level="WARNING",
                status="rejected",
                message="HTTP fallback message rejected because it was empty",
                payload={"participant_id": participant_id, "payload_keys": list(payload.keys())},
            )
            return {"saved": False, "reason": "empty message"}
        now = datetime.utcnow().isoformat()
        try:
            await _save_message(session_id, participant_id, text, now, source="http")
            return {"saved": True, "session_id": session_id, "participant_id": participant_id, "text": text, "created_at": now}
        except Exception as exc:
            await log_proto_exception(
                session_id=session_id,
                action="http_message_save",
                actor=participant_id,
                exc=exc,
                payload={"text": text, "created_at": now},
            )
            raise

    @app.websocket("/ws/{user_id}")
    async def websocket_endpoint(ws: WebSocket, user_id: str):
        """Compatibility WebSocket endpoint used by admin/facilitator pages."""
        audience = "admin" if user_id == "admin" else "facilitator" if user_id == "facilitator" else "participant"
        await connection_manager.connect(user_id, ws, audience=audience)
        await log_proto(
            session_id="global",
            action="websocket_connected",
            actor=audience,
            message=f"{audience} websocket connected",
            payload={"user_id": user_id, "audience": audience},
        )
        try:
            while True:
                data = await ws.receive_text()
                await log_proto(
                    session_id="global",
                    action="websocket_received",
                    actor=audience,
                    message=f"Received compatibility websocket payload from {audience}",
                    payload={"user_id": user_id, "text": data},
                )
                await connection_manager.send_to_user(user_id, {"type": "echo", "text": data})
        except WebSocketDisconnect:
            connection_manager.disconnect(user_id, audience=audience)
            await log_proto(
                session_id="global",
                action="websocket_disconnected",
                actor=audience,
                message=f"{audience} websocket disconnected",
                payload={"user_id": user_id, "audience": audience},
            )
        except Exception as exc:
            await log_proto_exception("global", "websocket_loop", audience, exc, {"user_id": user_id})
            connection_manager.disconnect(user_id, audience=audience)
            raise

    @app.websocket("/ws/{session_id}/{participant_id}")
    async def participant_websocket(ws: WebSocket, session_id: str, participant_id: str):
        """Participant WebSocket endpoint for live chat."""
        await connection_manager.connect_session(session_id, participant_id, ws)
        await log_proto(
            session_id=session_id,
            action="participant_ws_connected",
            actor=participant_id,
            message="Participant WebSocket connected",
            payload={"participant_id": participant_id},
        )
        await _register_participant(session_id, participant_id, source="websocket_connect")
        try:
            await ws.send_json({"type": "system", "text": "Connected", "session_id": session_id})
            await log_proto(
                session_id=session_id,
                action="participant_ws_system_sent",
                actor="system",
                message="Connection confirmation sent to participant",
                payload={"participant_id": participant_id},
            )
            while True:
                data = await ws.receive_json()
                await log_proto(
                    session_id=session_id,
                    action="participant_ws_payload_received",
                    actor=participant_id,
                    message="Participant WebSocket payload received",
                    payload={"participant_id": participant_id, "payload": data},
                )
                text = str(data.get("text") or "").strip()
                if not text:
                    await log_proto(
                        session_id=session_id,
                        action="participant_message_rejected",
                        actor=participant_id,
                        level="WARNING",
                        status="rejected",
                        message="Participant message ignored because it was empty",
                        payload={"payload": data},
                    )
                    continue
                now = datetime.utcnow().isoformat()
                await _save_message(session_id, participant_id, text, now, source="websocket")
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
                await log_proto(
                    session_id=session_id,
                    action="participant_message_broadcast",
                    actor="system",
                    message="Participant message saved and broadcast to session/admin/facilitator",
                    payload={"participant_id": participant_id, "text_length": len(text), "created_at": now},
                )
        except WebSocketDisconnect:
            connection_manager.disconnect_session(session_id, participant_id)
            await log_proto(
                session_id=session_id,
                action="participant_ws_disconnected",
                actor=participant_id,
                message="Participant WebSocket disconnected",
                payload={"participant_id": participant_id},
            )
        except Exception as exc:
            connection_manager.disconnect_session(session_id, participant_id)
            await log_proto_exception(
                session_id=session_id,
                action="participant_ws_loop",
                actor=participant_id,
                exc=exc,
                payload={"participant_id": participant_id},
            )
            raise

    return app


async def _register_participant(session_id: str, participant_id: str, source: str = "unknown") -> None:
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
    await log_proto(
        session_id=session_id,
        action="participant_registered_or_seen",
        actor=participant_id,
        message="Participant registered or last_seen_at updated",
        payload={"participant_id": participant_id, "source": source, "timestamp": now},
    )


async def _save_message(session_id: str, participant_id: str, text: str, created_at: str, source: str = "unknown") -> None:
    await _register_participant(session_id, participant_id, source=f"message:{source}")
    await execute(
        "INSERT INTO messages (session_id, participant_id, text, created_at) VALUES (?, ?, ?, ?)",
        (session_id, participant_id, text, created_at),
    )
    await log_event(session_id, participant_id, "message", {"session_id": session_id, "user_id": participant_id, "text": text})
    await log_proto(
        session_id=session_id,
        action="message_saved",
        actor=participant_id,
        message="Participant message persisted in messages and events tables",
        payload={"participant_id": participant_id, "source": source, "text": text, "text_length": len(text), "created_at": created_at},
    )


app = create_app()
