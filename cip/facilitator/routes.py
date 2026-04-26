"""Facilitator routes for CIP.

Currently provides minimal endpoints. Extend with session management APIs.
"""
from __future__ import annotations

from fastapi import APIRouter


router = APIRouter()


@router.post("/facilitator/api/session/start")
async def start_session():
    """Start a new session (placeholder)."""
    return {"status": "started"}