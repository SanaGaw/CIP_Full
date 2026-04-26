"""Admin routes for CIP.

This module defines HTTP and WebSocket endpoints for the operator dashboard.
For the pilot build we provide minimal endpoints for configuration and health.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..config import get_settings


router = APIRouter()


@router.get("/health")
async def health():
    """Simple health check endpoint."""
    return {"status": "ok"}


@router.get("/admin/api/config")
async def get_config(settings=Depends(get_settings)):
    """Return current configuration values."""
    return settings.model_dump()