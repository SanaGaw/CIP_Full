"""Tier routing for LLM calls.

This module defines the core function `call_with_tier` which selects a model
provider chain based on the task identifier and calls the appropriate LLM
client. It also handles caching and trace logging.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Tuple

from ..config import settings
from ..observability import log_trace
from .cache import cache
from .clients import call_anthropic, call_openrouter, call_gemini, call_groq
from .tier_map import DEFAULT_TIER_MAP, TIER_PROVIDERS


PROVIDERS = {
    "anthropic": call_anthropic,
    "openrouter": call_openrouter,
    "gemini": call_gemini,
    "groq": call_groq,
}


async def call_with_tier(
    task_id: str,
    system: str,
    messages: list,
    max_tokens: int,
    temperature: float,
    session_id: str,
) -> Dict[str, Any]:
    """Call an LLM according to the tier mapped to the given task identifier.

    This function implements fallback between providers, caching (unless
    pilot mode is enabled), and trace logging.
    """
    tier = DEFAULT_TIER_MAP.get(task_id, "T0")
    provider_chain: List[Tuple[str, str]] = TIER_PROVIDERS.get(tier, [])

    # Bypass cache entirely when pilot mode is enabled
    use_cache = not settings.pilot_mode and tier != "T0"

    # Try cache lookup
    if use_cache and provider_chain:
        first_model = provider_chain[0][1]
        cached = cache.get(system, messages, first_model)
        if cached:
            # Trace cached usage
            await log_trace(
                session_id,
                "llm_cache_hit",
                "tier_router",
                f"Using cached response for task {task_id}",
                inputs={"tier": tier, "task_id": task_id},
                outputs=cached,
                reasoning="Cache hit",
            )
            return cached

    # Iterate through providers in order
    for index, (provider_name, model) in enumerate(provider_chain):
        client_fn = PROVIDERS.get(provider_name)
        if not client_fn:
            continue
        try:
            result = await client_fn(model, system, messages, max_tokens, temperature)
            # If we succeed, cache it if caching enabled
            if use_cache:
                cache.set(system, messages, model, result)
            # Log trace
            await log_trace(
                session_id,
                "llm_call",
                "tier_router",
                f"LLM call for task {task_id}",
                inputs={
                    "task_id": task_id,
                    "tier": tier,
                    "provider": provider_name,
                    "model": model,
                    "fallback_index": index,
                    "messages": messages,
                },
                outputs=result,
                reasoning="Successful call",
            )
            return result
        except Exception as exc:
            # On error, log and try next provider
            await log_trace(
                session_id,
                "llm_call_error",
                "tier_router",
                f"LLM call failed for task {task_id} on provider {provider_name}",
                inputs={"task_id": task_id, "provider": provider_name, "model": model},
                outputs={"error": str(exc)},
                reasoning="Fallback to next provider",
            )
            continue

    # If all providers fail, return an empty stub result
    fallback_response = {
        "text": "",
        "input_tokens": 0,
        "output_tokens": 0,
        "model": "none",
        "provider": "none",
        "latency_ms": 0,
    }
    await log_trace(
        session_id,
        "llm_call_fallback",
        "tier_router",
        f"All providers failed for task {task_id}",
        inputs={"task_id": task_id},
        outputs=fallback_response,
        reasoning="No provider available",
    )
    return fallback_response