"""Simple LLM cache implementation.

This module provides a simple in-memory cache for LLM responses keyed by a
hash of the prompt and model. In a production setting you would persist this
to a database. The cache can be disabled by setting `PILOT_MODE=True` in the
application settings.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Dict, Optional, Tuple

from ..config import settings


class LLMCache:
    """In-memory cache of LLM responses keyed by SHA-256 of (system + messages + model)."""

    def __init__(self) -> None:
        self.store: Dict[str, Tuple[dict, float]] = {}
        self.ttl_seconds: int = 3600  # default TTL of 1 hour

    @staticmethod
    def _hash_prompt(system: str, messages: list, model: str) -> str:
        key = json.dumps({"system": system, "messages": messages, "model": model}, sort_keys=True).encode("utf-8")
        return hashlib.sha256(key).hexdigest()

    def get(self, system: str, messages: list, model: str) -> Optional[dict]:
        """Return a cached response if available and not expired."""
        h = self._hash_prompt(system, messages, model)
        entry = self.store.get(h)
        if not entry:
            return None
        response, created = entry
        if time.time() - created > self.ttl_seconds:
            del self.store[h]
            return None
        return response

    def set(self, system: str, messages: list, model: str, response: dict) -> None:
        """Store a response in the cache."""
        h = self._hash_prompt(system, messages, model)
        self.store[h] = (response, time.time())


cache = LLMCache()