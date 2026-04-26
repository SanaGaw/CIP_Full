"""Bridging engine for delivering ideas.

This module implements logic to decide how to present a new idea to a user.
The decision is based on similarity between the idea and the user's stance.
"""
from __future__ import annotations

from typing import Dict, Any

from ..nlp.embeddings import embed


def bridge(new_idea: str, user_profile: Dict[str, Any], orchestrator_hint: str | None, current_turn: int) -> Dict[str, Any]:
    """Compute a bridging mode for a new idea.

    Args:
        new_idea: The idea text to deliver.
        user_profile: The target user's profile.
        orchestrator_hint: A hint from the orchestrator (extend/probe/challenge).
        current_turn: The current conversation turn index.

    Returns:
        A dictionary containing the chosen mode and associated metadata.
    """
    # Compute simple cosine similarity between idea embedding and user's stance summary.
    # Real implementation should use user's stance history; here we use a dummy value.
    similarity_score = 0.5  # placeholder constant
    stance_signal = "neutral"
    mode = orchestrator_hint or "PROBE"
    if similarity_score >= 0.60:
        mode = "EXTEND"
    elif similarity_score <= 0.25:
        mode = "PROBE"
    else:
        mode = "CHALLENGE"

    # Bayesian override would go here
    # Anchoring detection would override to CHALLENGE

    return {
        "mode": mode,
        "idea": new_idea,
        "connection": None,
        "similarity_score": similarity_score,
        "stance_signal": stance_signal,
    }