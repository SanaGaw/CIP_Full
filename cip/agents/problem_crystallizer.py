"""Problem Crystallizer agent.

This agent synthesises narrative elements and clusters into a problem
statement. For now it returns a simple structure based on provided input.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..observability import log_trace


async def problem_crystallizer(session_id: str, narrative_elements: List[Dict[str, Any]], clusters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a problem statement proposal from narrative elements and clusters.

    Args:
        session_id: The current session identifier.
        narrative_elements: A list of parsed narrative elements.
        clusters: A list of idea clusters.

    Returns:
        A dict containing a proposed problem statement and related fields.
    """
    # Very naive synthesis: just count actors and mention them
    actors = []
    for item in narrative_elements:
        actors.extend(item.get("actors", []))
    affected = list(set(actors)) or ["stakeholders"]
    statement = f"The current state prevents {', '.join(affected)} from achieving their goals."
    result = {
        "problem_statement": statement[:60],
        "current_state": "",
        "desired_state": "",
        "measurable_consequence": "",
        "affected_parties": affected,
        "root_cause_hypothesis": "",
        "framing_tension": "",
        "confidence": 0.0,
    }
    await log_trace(
        session_id,
        "problem_crystallizer",
        "problem_crystallizer",
        "Generated problem statement",
        inputs={"narrative_elements": narrative_elements, "clusters": clusters},
        outputs=result,
        reasoning="Stub problem crystallizer",
    )
    return result