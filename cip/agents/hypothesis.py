"""Hypothesis generation agent.

Generates falsifiable hypotheses based on clusters using LLM via call_with_tier.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from ..observability import log_trace
from ..llm.tier_router import call_with_tier


HYP_GENERATE_SYSTEM = """You are the Hypothesis Generator in a CIP session. Your role is to generate
falsifiable hypotheses about root causes based on the idea clusters identified.

Generate 2-3 hypotheses that:
1. Are grounded in the evidence from the idea clusters
2. Are falsifiable (can be proven wrong)
3. Explain why the identified problems exist
4. Include what would support or contradict each hypothesis

Return a JSON object with a 'hypotheses' array, each containing:
- id: Unique identifier (H1, H2, H3)
- statement: The hypothesis statement in "We believe X because Y" format
- would_support: List of cluster IDs or themes that support this hypothesis
- would_contradict: List of cluster IDs or themes that would contradict this hypothesis
- confidence: Initial confidence level (0-1)

Be analytical and evidence-based."""


async def generate_hypotheses(session_id: str, clusters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate hypotheses about root causes.

    Args:
        session_id: The current session identifier.
        clusters: List of idea clusters.

    Returns:
        A dict containing a list of hypotheses.
    """
    # Build cluster summary for LLM
    cluster_info = []
    for i, c in enumerate(clusters[:5]):
        ideas = c.get("ideas", [])
        themes = [idea.get("text", "")[:100] for idea in ideas[:3]]
        cluster_info.append({
            "id": c.get("cluster_id", f"cluster_{i}"),
            "theme": c.get("theme", "general"),
            "size": len(ideas),
            "sample_ideas": themes,
        })

    user_message = f"""Idea Clusters to analyze:
{json.dumps(cluster_info, indent=2)}

Based on these clusters, generate falsifiable hypotheses about the root causes
of the identified problems. Each hypothesis should:
- State what we believe is true
- Explain the reasoning
- Identify what evidence would support or contradict it"""

    try:
        # Call LLM via tier router for hypothesis generation
        result = await call_with_tier(
            task_id="hyp.generate",
            system=HYP_GENERATE_SYSTEM,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=600,
            temperature=0.4,
            session_id=session_id,
        )
        llm_text = result.get("text", "")

        # Try to parse JSON from LLM response
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', llm_text, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
                hypotheses = parsed.get("hypotheses", [])
            except json.JSONDecodeError:
                hypotheses = _fallback_hypotheses(clusters)
        else:
            hypotheses = _fallback_hypotheses(clusters)

        # Ensure we have at least 2 hypotheses
        if len(hypotheses) < 2:
            hypotheses = _fallback_hypotheses(clusters)

    except Exception as e:
        # Fallback on any error
        hypotheses = _fallback_hypotheses(clusters)

    final_result = {"hypotheses": hypotheses}
    await log_trace(
        session_id,
        "hypothesis_generate",
        "hypothesis_agent",
        "Generated hypotheses",
        inputs={"clusters": clusters},
        outputs=final_result,
        reasoning="LLM-powered hypothesis generation",
    )
    return final_result


def _fallback_hypotheses(clusters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fallback hypotheses when LLM is unavailable."""
    cluster_ids = [c.get("cluster_id", "") for c in clusters[:2]]
    return [
        {
            "id": "H1",
            "statement": "We believe structural factors are the primary driver of the identified challenges. This hypothesis is supported by patterns in the idea clusters and would be weakened if opposing evidence emerges.",
            "would_support": cluster_ids[:1] if cluster_ids else ["initial_cluster"],
            "would_contradict": cluster_ids[1:] if len(cluster_ids) > 1 else [],
            "confidence": 0.5,
        },
        {
            "id": "H2",
            "statement": "We believe process inefficiencies are contributing significantly to the problem. This would be supported by evidence of workflow gaps and contradicted by success stories in similar contexts.",
            "would_support": cluster_ids[1:] if len(cluster_ids) > 1 else ["process_cluster"],
            "would_contradict": cluster_ids[:1] if cluster_ids else [],
            "confidence": 0.4,
        },
    ]
