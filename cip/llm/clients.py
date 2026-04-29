"""LLM client implementations.

This module provides async functions to call various LLM providers with real HTTP calls.
When API keys are missing, the functions skip gracefully without failing.
"""
from __future__ import annotations

import httpx
import time
from typing import Any, Dict

from ..config import settings


async def call_anthropic(model: str, system: str, messages: list, max_tokens: int, temperature: float) -> Dict[str, Any]:
    """Call the Anthropic API with real HTTP requests."""
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": messages,
    }
    t0 = time.time()
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=body
        )
        response.raise_for_status()
        data = response.json()

    text = data["content"][0]["text"]
    usage = data.get("usage", {})
    return {
        "text": text,
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "model": model,
        "provider": "anthropic",
        "latency_ms": int((time.time() - t0) * 1000),
    }


async def call_openrouter(model: str, system: str, messages: list, max_tokens: int, temperature: float) -> Dict[str, Any]:
    """Call the OpenRouter API with real HTTP requests."""
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/SanaGaw/CIP_Full",
        "X-Title": "CIP",
    }
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}] + messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    t0 = time.time()
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=body
        )
        response.raise_for_status()
        data = response.json()

    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return {
        "text": text,
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
        "model": model,
        "provider": "openrouter",
        "latency_ms": int((time.time() - t0) * 1000),
    }


async def call_gemini(model: str, system: str, messages: list, max_tokens: int, temperature: float) -> Dict[str, Any]:
    """Call the Google Gemini API with real HTTP requests."""
    if not settings.google_ai_api_key:
        raise RuntimeError("GOOGLE_AI_API_KEY not set")

    # Gemini API format
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.google_ai_api_key}"

    # Convert messages to Gemini format
    contents = []
    for msg in messages:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    body = {
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        },
        "systemInstruction": {"parts": [{"text": system}]},
    }

    t0 = time.time()
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, json=body)
        response.raise_for_status()
        data = response.json()

    text = data["candidates"][0]["content"]["parts"][0]["text"]
    usage = data.get("usageMetadata", {})
    return {
        "text": text,
        "input_tokens": usage.get("promptTokenCount", 0),
        "output_tokens": usage.get("candidatesTokenCount", 0),
        "model": model,
        "provider": "gemini",
        "latency_ms": int((time.time() - t0) * 1000),
    }


async def call_groq(model: str, system: str, messages: list, max_tokens: int, temperature: float) -> Dict[str, Any]:
    """Call the Groq API with real HTTP requests."""
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY not set")

    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}] + messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    t0 = time.time()
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=body
        )
        response.raise_for_status()
        data = response.json()

    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return {
        "text": text,
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
        "model": model,
        "provider": "groq",
        "latency_ms": int((time.time() - t0) * 1000),
    }