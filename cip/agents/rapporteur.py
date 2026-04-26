"""Rapporteur agent placeholder.

The rapporteur summarises the session at various points and produces the final
advisory report. In this pilot build we provide stubs that log actions.
"""
from __future__ import annotations

from typing import Any, Dict

from ..observability import log_trace


class Rapporteur:
    """Rapporteur stub implementation."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id

    async def live_status(self) -> Dict[str, Any]:
        """Send a live status update (placeholder)."""
        await log_trace(
            self.session_id,
            "rapporteur_live",
            "rapporteur",
            "Live status update",
            reasoning="Stub live status",
        )
        return {}

    async def phase_close(self, phase: str) -> Dict[str, Any]:
        """Summarise the closing of a phase."""
        await log_trace(
            self.session_id,
            "rapporteur_phase_close",
            "rapporteur",
            f"Phase {phase} closed",
            inputs={"phase": phase},
            outputs={},
            reasoning="Stub phase close",
        )
        return {}

    async def final_report(self) -> Dict[str, Any]:
        """Generate the final report (placeholder)."""
        await log_trace(
            self.session_id,
            "rapporteur_final_report",
            "rapporteur",
            "Final report generated",
            reasoning="Stub final report",
        )
        return {"report": "This is a placeholder report."}