"""Main entry point for the CIP FastAPI application.

This module sets up the FastAPI app, initialises the database, configures
routing for participants, administrators and facilitators, and mounts
static files and templates.
"""
from __future__ import annotations

import logging
from pathlib import Path
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .db import init_db
from .observability import log_event
from .state import connection_manager
from .websocket.manager import ConnectionManager
from .admin.routes import router as admin_router
from .facilitator.routes import router as facilitator_router


logger = logging.getLogger(__name__)
settings = get_settings()


def create_app() -> FastAPI:
    """Create and configure a FastAPI application."""
    app = FastAPI(title="CIP v2")

    # CORS (allow all origins for dev)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialise database on startup
    @app.on_event("startup")
    async def startup_event() -> None:
        await init_db()
        global connection_manager
        connection_manager = ConnectionManager()
        logger.info("Database initialised and connection manager ready")

    # Routes
    app.include_router(admin_router, prefix="")
    app.include_router(facilitator_router, prefix="")

    # Static files and templates
    app.mount("/static", StaticFiles(directory="cip/static"), name="static")

    def render_html(path: str) -> HTMLResponse:
        file_path = Path(__file__).resolve().parent / path
        return HTMLResponse(file_path.read_text(encoding="utf-8"))

    @app.get("/")
    async def root():
        return {"message": "CIP v2 API"}

    @app.get("/admin")
    async def admin_dashboard():
        return render_html("templates/admin/dashboard.html")

    @app.get("/facilitator")
    async def facilitator_dashboard():
        return render_html("templates/facilitator/dashboard.html")

    @app.get("/participant")
    async def participant_chat():
        return render_html("templates/participant/chat.html")

    @app.websocket("/ws/{user_id}")
    async def websocket_endpoint(ws: WebSocket, user_id: str):
        """Handle participant WebSocket connections."""
        await connection_manager.connect(user_id, ws, audience="participant")
        try:
            while True:
                data = await ws.receive_text()
                await log_event("session", user_id, "message", {"user_id": user_id, "text": data})
                # Echo back for now
                await connection_manager.send_to_user(user_id, {"echo": data})
        except WebSocketDisconnect:
            connection_manager.disconnect(user_id, audience="participant")

    return app


app = create_app()