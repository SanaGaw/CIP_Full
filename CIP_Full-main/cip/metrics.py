"""Metrics utilities for CIP v2.

This module implements synthetic idea ratio and other auditing functions
with real database-backed computations.
"""
from __future__ import annotations

from typing import Dict, List, Any
import json


async def compute_synthetic_idea_ratio(session_id: str) -> Dict[str, float | int]:
    """Compute the synthetic idea ratio for a session.

    Analyzes idea authorship patterns to identify potential synthetic (non-original) ideas
    based on similarity to other participants' ideas.

    Args:
        session_id: The session identifier.

    Returns:
        Dictionary with synthetic ratio metrics by participant and overall.
    """
    try:
        # Import here to avoid circular imports
        from .db import get_db

        async with get_db() as db:
            # Fetch ideas for this session
            ideas = await db.fetch_all(
                """
                SELECT i.*, u.participant_type
                FROM ideas i
                JOIN participants u ON i.participant_id = u.id
                WHERE i.session_id = $1
                ORDER BY i.created_at
                """,
                session_id,
            )

            if not ideas:
                return {
                    "A": 0, "B": 0, "C": 0,
                    "synthetic_ratio": 0.0,
                    "weighted_ratio": 0.0,
                    "total_ideas": 0,
                }

            # Group ideas by participant type
            participant_ideas: Dict[str, List[str]] = {}
            for idea in ideas:
                ptype = idea.get("participant_type", "C")
                text = idea.get("text", "")
                if text:
                    participant_ideas.setdefault(ptype, []).append(text)

            # Compute synthetic ratios
            synthetic_counts: Dict[str, int] = {"A": 0, "B": 0, "C": 0}
            thresholds = {"A": 0.85, "B": 0.80, "C": 0.75}

            for idea in ideas:
                text = idea.get("text", "")
                ptype = idea.get("participant_type", "C")
                if not text:
                    continue

                # Check similarity to other participants' ideas
                is_synthetic = False
                threshold = thresholds.get(ptype, 0.80)

                for other_ptype, other_texts in participant_ideas.items():
                    if other_ptype == ptype:
                        continue
                    for other_text in other_texts:
                        similarity = _simple_similarity(text, other_text)
                        if similarity >= threshold:
                            is_synthetic = True
                            break
                    if is_synthetic:
                        break

                if is_synthetic:
                    synthetic_counts[ptype] = synthetic_counts.get(ptype, 0) + 1

            # Compute ratios
            total = len(ideas)
            synthetic_a = synthetic_counts.get("A", 0)
            synthetic_b = synthetic_counts.get("B", 0)
            synthetic_c = synthetic_counts.get("C", 0)
            total_synthetic = synthetic_a + synthetic_b + synthetic_c

            return {
                "A": synthetic_a,
                "B": synthetic_b,
                "C": synthetic_c,
                "synthetic_ratio": total_synthetic / total if total > 0 else 0.0,
                "weighted_ratio": (synthetic_a * 1.0 + synthetic_b * 0.7 + synthetic_c * 0.3) / total if total > 0 else 0.0,
                "total_ideas": total,
            }

    except Exception:
        # Fallback for when DB is unavailable
        return {
            "A": 0, "B": 0, "C": 0,
            "synthetic_ratio": 0.0,
            "weighted_ratio": 0.0,
        }


def _simple_similarity(text1: str, text2: str) -> float:
    """Compute simple word-overlap similarity between two texts."""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union) if union else 0.0


async def compute_died_unfairly(session_id: str) -> List[dict]:
    """Identify clusters that did not circulate fairly.

    Analyzes whether all clusters received adequate discussion and representation
    in the session.

    Args:
        session_id: The session identifier.

    Returns:
        List of clusters that died unfairly (were underrepresented).
    """
    try:
        from .db import get_db

        async with get_db() as db:
            # Fetch cluster statistics
            clusters = await db.fetch_all(
                """
                SELECT c.id, c.theme, c.size,
                       COALESCE(d.mention_count, 0) as mention_count,
                       COALESCE(d.discussion_duration, 0) as discussion_duration
                FROM clusters c
                LEFT JOIN (
                    SELECT cluster_id,
                           COUNT(*) as mention_count,
                           SUM(duration_seconds) as discussion_duration
                    FROM discussions
                    WHERE session_id = $1
                    GROUP BY cluster_id
                ) d ON c.id = d.cluster_id
                WHERE c.session_id = $1
                """,
                session_id,
            )

            if not clusters:
                return []

            # Calculate thresholds
            avg_size = sum(c.get("size", 0) for c in clusters) / len(clusters)
            avg_mentions = sum(c.get("mention_count", 0) for c in clusters) / len(clusters)

            # Identify clusters that died unfairly
            died_unfairly = []
            for cluster in clusters:
                size_ratio = cluster.get("size", 0) / avg_size if avg_size > 0 else 1.0
                mention_ratio = cluster.get("mention_count", 0) / avg_mentions if avg_mentions > 0 else 1.0

                # Died unfairly if: large cluster but low mention ratio
                if size_ratio > 1.5 and mention_ratio < 0.5:
                    died_unfairly.append({
                        "cluster_id": cluster.get("id"),
                        "theme": cluster.get("theme"),
                        "size": cluster.get("size"),
                        "mention_count": cluster.get("mention_count"),
                        "reason": f"Large cluster (size ratio: {size_ratio:.2f}) but low representation (mention ratio: {mention_ratio:.2f})",
                        "severity": "high" if mention_ratio < 0.25 else "medium",
                    })
                elif cluster.get("mention_count", 0) == 0 and cluster.get("size", 0) > 0:
                    died_unfairly.append({
                        "cluster_id": cluster.get("id"),
                        "theme": cluster.get("theme"),
                        "size": cluster.get("size"),
                        "mention_count": 0,
                        "reason": "Cluster received zero discussion despite having ideas",
                        "severity": "high",
                    })

            return died_unfairly

    except Exception:
        return []
