"""Devil's advocate agent placeholder.

In future steps this agent will inject contrarian perspectives to challenge
the group's assumptions and surface unseen risks.
"""
from __future__ import annotations

from typing import Any, Dict

from ..observability import log_trace


class DevilAgent:
    """Devil's advocate stub."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id

    async def trigger(self, phase: str) -> Dict[str, Any]:
        """Trigger the devil agent for a given phase.

        Args:
            phase: The current session phase.

        Returns:
            A dict with any generated challenges or stress tests.
        """
        await log_trace(
            self.session_id,
            "devil_trigger",
            "devil",
            f"Devil triggered in phase {phase}",
            inputs={"phase": phase},
            outputs={},
            reasoning="Stub devil agent",
        )
        return {}