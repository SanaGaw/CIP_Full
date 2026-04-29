"""Problem Crystallizer agent.

This agent synthesises narrative elements and clusters into a problem
statement using LLM-powered synthesis via call_with_tier.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from ..observability import log_trace
from ..llm.tier_router import call_with_tier


PC_SYNTHESIZE_SYSTEM = """You are the Problem Crystallizer in a CIP session. Your role is to synthesize
narrative elements and idea clusters into a coherent problem statement.

Analyze the provided narrative elements (actors, events, consequences, stakes) and
cluster information to generate a structured problem statement.

Return a JSON object with these fields:
- problem_statement: A concise 1-2 sentence problem statement
- current_state: Description of the current problematic situation
- desired_state: What success looks like
- measurable_consequence: Quantifiable impact of the problem
- affected_parties: List of stakeholders impacted
- root_cause_hypothesis: Initial hypothesis about root cause
- framing_tension: Key tension or trade-off to navigate
- confidence: Your confidence score (0-1)

Be specific and grounded in the provided evidence."""


async def problem_crystallizer(session_id: str, narrative_elements: List[Dict[str, Any]], clusters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a problem statement proposal from narrative elements and clusters.

    Args:
        session_id: The current session identifier.
        narrative_elements: A list of parsed narrative elements.
        clusters: A list of idea clusters.

    Returns:
        A dict containing a proposed problem statement and related fields.
    """
    # Extract actors from narrative elements
    actors = []
    events = []
    consequences = []
    stakes = []
    for item in narrative_elements:
        actors.extend(item.get("actors", []))
        events.extend(item.get("events", []))
        consequences.extend(item.get("consequences", []))
        stakes.extend(item.get("stakes", []))

    affected = list(set(actors)) or ["stakeholders"]
    cluster_summary = [c.get("theme", "general") for c in clusters[:5]]

    # Build user message for LLM synthesis
    user_message = f"""Narrative Elements:
- Actors: {', '.join(actors[:10]) if actors else 'None identified'}
- Events: {', '.join(events[:10]) if events else 'None identified'}
- Consequences: {', '.join(consequences[:10]) if consequences else 'None identified'}
- Stakes: {', '.join(stakes[:10]) if stakes else 'None identified'}

Idea Clusters: {', '.join(cluster_summary) if cluster_summary else 'No clusters yet'}

Affected parties: {', '.join(affected)}

Synthesize this into a structured problem statement."""

    try:
        # Call LLM via tier router for synthesis
        result = await call_with_tier(
            task_id="pc.synthesize",
            system=PC_SYNTHESIZE_SYSTEM,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=500,
            temperature=0.3,
            session_id=session_id,
        )
        llm_text = result.get("text", "")

        # Try to parse JSON from LLM response
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', llm_text, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
                final_result = {
                    "problem_statement": parsed.get("problem_statement", ""),
                    "current_state": parsed.get("current_state", ""),
                    "desired_state": parsed.get("desired_state", ""),
                    "measurable_consequence": parsed.get("measurable_consequence", ""),
                    "affected_parties": parsed.get("affected_parties", affected),
                    "root_cause_hypothesis": parsed.get("root_cause_hypothesis", ""),
                    "framing_tension": parsed.get("framing_tension", ""),
                    "confidence": parsed.get("confidence", 0.5),
                }
            except json.JSONDecodeError:
                final_result = _fallback_synthesis(affected, llm_text)
        else:
            final_result = _fallback_synthesis(affected, llm_text)

    except Exception as e:
        # Fallback on any error
        final_result = _fallback_synthesis(affected, str(e))

    await log_trace(
        session_id,
        "problem_crystallizer",
        "problem_crystallizer",
        "Generated problem statement",
        inputs={"narrative_elements": narrative_elements, "clusters": clusters},
        outputs=final_result,
        reasoning="LLM-powered problem crystallizer synthesis",
    )
    return final_result


def _fallback_synthesis(affected: List[str], context: str = "") -> Dict[str, Any]:
    """Fallback synthesis when LLM is unavailable."""
    affected_str = ', '.join(affected) if affected else "stakeholders"
    return {
        "problem_statement": f"The current state prevents {affected_str} from achieving optimal outcomes.",
        "current_state": "Challenges have been identified that require structured analysis.",
        "desired_state": "Improved outcomes through systematic problem-solving.",
        "measurable_consequence": "Impact to be determined upon further analysis.",
        "affected_parties": affected,
        "root_cause_hypothesis": "Multiple factors contributing; further investigation needed.",
        "framing_tension": "Balance between comprehensive analysis and timely action.",
        "confidence": 0.3,
    }
