"""WebSocket connection manager.

This module manages active WebSocket connections and provides methods to
send messages to individual users, participants, administrators and
facilitators. The implementation is minimal and does not handle reconnection.
"""
from __future__ import annotations

from typing import Dict, List

from fastapi import WebSocket


class ConnectionManager:
    """Manage WebSocket connections for different audiences."""

    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}
        self.admin_connections: List[WebSocket] = []
        self.facilitator_connections: List[WebSocket] = []

    async def connect(self, user_id: str, websocket: WebSocket, audience: str = "participant") -> None:
        """Register a new connection."""
        await websocket.accept()
        if audience == "participant":
            self.active_connections[user_id] = websocket
        elif audience == "admin":
            self.admin_connections.append(websocket)
        elif audience == "facilitator":
            self.facilitator_connections.append(websocket)

    def disconnect(self, user_id: str, audience: str = "participant") -> None:
        """Remove a connection."""
        if audience == "participant" and user_id in self.active_connections:
            del self.active_connections[user_id]
        elif audience == "admin":
            if user_id in self.active_connections:
                del self.active_connections[user_id]

    async def send_to_user(self, user_id: str, message: dict) -> None:
        """Send a message to a single user."""
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_json(message)

    async def broadcast_participants(self, message: dict) -> None:
        """Broadcast a message to all participants."""
        for ws in list(self.active_connections.values()):
            await ws.send_json(message)

    async def broadcast_admin(self, message: dict) -> None:
        """Broadcast a message to all admin connections."""
        for ws in self.admin_connections:
            await ws.send_json(message)

    async def broadcast_facilitator(self, message: dict) -> None:
        """Broadcast a message to all facilitator connections."""
        for ws in self.facilitator_connections:
            await ws.send_json(message)