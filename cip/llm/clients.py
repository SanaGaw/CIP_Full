"""LLM client implementations.

This module provides async functions to call various LLM providers. In this
pilot build we stub out the external calls. Replace the stubs with real API
requests when API keys are configured.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict


async def call_anthropic(model: str, system: str, messages: list, max_tokens: int, temperature: float) -> Dict[str, Any]:
    """Call the Anthropic API.

    This stub returns a fixed response. Replace with a real API call.
    """
    # TODO: implement actual API call to Anthropic
    await asyncio.sleep(0.01)
    return {
        "text": "[anthropic] stub response",
        "input_tokens": 0,
        "output_tokens": 0,
        "model": model,
        "provider": "anthropic",
        "latency_ms": 0,
    }


async def call_openrouter(model: str, system: str, messages: list, max_tokens: int, temperature: float) -> Dict[str, Any]:
    """Call the OpenRouter API.

    This stub returns a fixed response. Replace with a real API call.
    """
    await asyncio.sleep(0.01)
    return {
        "text": "[openrouter] stub response",
        "input_tokens": 0,
        "output_tokens": 0,
        "model": model,
        "provider": "openrouter",
        "latency_ms": 0,
    }


async def call_gemini(model: str, system: str, messages: list, max_tokens: int, temperature: float) -> Dict[str, Any]:
    """Call the Google Gemini API (stub)."""
    await asyncio.sleep(0.01)
    return {
        "text": "[gemini] stub response",
        "input_tokens": 0,
        "output_tokens": 0,
        "model": model,
        "provider": "gemini",
        "latency_ms": 0,
    }


async def call_groq(model: str, system: str, messages: list, max_tokens: int, temperature: float) -> Dict[str, Any]:
    """Call the Groq API (stub)."""
    await asyncio.sleep(0.01)
    return {
        "text": "[groq] stub response",
        "input_tokens": 0,
        "output_tokens": 0,
        "model": model,
        "provider": "groq",
        "latency_ms": 0,
    }