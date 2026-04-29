"""Bridging engine for delivering ideas.

This module implements logic to decide how to present a new idea to a user.
The decision is based on similarity between the idea and the user's stance.
"""
from __future__ import annotations

from typing import Dict, Any, List
import numpy as np

from ..nlp.embeddings import embed


def compute_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """Compute cosine similarity between two embeddings."""
    e1 = np.array(embedding1)
    e2 = np.array(embedding2)
    norm1 = np.linalg.norm(e1)
    norm2 = np.linalg.norm(e2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(e1, e2) / (norm1 * norm2))


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
    # Compute real similarity using embeddings
    stance_signal = "neutral"
    similarity_score = 0.5

    try:
        # Get user's stance summary or stance history
        stance_history = user_profile.get("stance_history", [])
        stance_summary = user_profile.get("stance_summary", "")

        if stance_history:
            # Average embeddings of stance history
            stance_embeddings = []
            for stance in stance_history[-5:]:  # Last 5 stances
                stance_text = stance.get("text", "")
                if stance_text:
                    stance_embeddings.append(embed(stance_text))
            if stance_embeddings:
                avg_stance = np.mean(stance_embeddings, axis=0)
                idea_emb = embed(new_idea)
                similarity_score = compute_similarity(idea_emb.tolist(), avg_stance.tolist())
                stance_signal = "aligned" if similarity_score > 0.6 else "divergent"
        elif stance_summary:
            # Use stance summary for similarity
            summary_emb = embed(stance_summary)
            idea_emb = embed(new_idea)
            similarity_score = compute_similarity(idea_emb.tolist(), summary_emb.tolist())
            stance_signal = "aligned" if similarity_score > 0.6 else "divergent"
        else:
            # No stance data available, use moderate similarity
            similarity_score = 0.5
            stance_signal = "neutral"

    except Exception:
        # Fallback on any error
        similarity_score = 0.5
        stance_signal = "neutral"

    # Determine mode based on similarity
    mode = orchestrator_hint or "PROBE"
    if similarity_score >= 0.60:
        mode = "EXTEND"
    elif similarity_score <= 0.25:
        mode = "PROBE"
    else:
        mode = "CHALLENGE"

    # Bayesian override based on confidence
    confidence = user_profile.get("confidence", 0.5)
    if confidence < 0.3:
        mode = "PROBE"  # Low confidence suggests probe

    # Anchoring detection: if user has been repeating similar ideas
    if stance_history and len(stance_history) > 3:
        recent_similarities = []
        for stance in stance_history[-3:]:
            try:
                sim = compute_similarity(embed(new_idea).tolist(), embed(stance.get("text", "")).tolist())
                recent_similarities.append(sim)
            except Exception:
                pass
        if recent_similarities and np.mean(recent_similarities) > 0.8:
            mode = "CHALLENGE"  # Anchoring detected, challenge the pattern

    return {
        "mode": mode,
        "idea": new_idea,
        "connection": None,
        "similarity_score": round(similarity_score, 3),
        "stance_signal": stance_signal,
    }
