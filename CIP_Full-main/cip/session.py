"""Session state machine for CIP.

This module defines the phase configuration and helpers to advance the
session through the seven phases of deliberation. It is intentionally
minimal at this stage and should be extended as functionality is implemented.
"""
from __future__ import annotations

from typing import Dict, Optional

from .state import SessionState


# Phase configuration as specified in the build prompt. See state.PHASE_CONFIG for
# the fully detailed contract. Here we replicate the high-level structure.
PHASE_CONFIG: Dict[str, Dict[str, object]] = {
    "onboarding": {
        "next": "define",
        "target_mode": None,
        "auto_advance": "all_participants_onboarded",
        "conv_modes": ["LISTEN"],
        "silent_generation": False,
        "devil_active": False,
    },
    "define": {
        "next": "divergence",
        "target_mode": "clarify_tensions",
        "auto_advance": "admin_closes_phase",
        "conv_modes": ["LISTEN", "NARRATE", "REFLECT"],
        "silent_generation": False,
        "devil_active": False,
        "on_close": ["problem_crystallizer", "hypothesis_agent"],
    },
    "divergence": {
        "next": "exploration",
        "target_mode": "explore",
        "auto_advance": "diversity_plateau_or_timer",
        "conv_modes": ["LISTEN", "REFLECT", "BRIDGE"],
        "silent_generation": True,
        "silent_duration_minutes_default": 5,
        "devil_active": True,
        "devil_framework": "lateral_thinking",
        "stagnation_n": 5,
    },
    "exploration": {
        "next": "criteria",
        "target_mode": "clarify_tensions",
        "auto_advance": "diversity_plateau_or_timer",
        "conv_modes": ["LISTEN", "REFLECT", "BRIDGE", "RECALL"],
        "silent_generation": False,
        "devil_active": True,
        "devil_framework": "blue_ocean_4_actions",
        "stagnation_n": 3,
    },
    "criteria": {
        "next": "evaluation",
        "target_mode": "prioritize",
        "auto_advance": "all_ahp_submitted",
        "conv_modes": ["CRITERIA"],
        "silent_generation": False,
        "devil_active": True,
        "devil_framework": "scamper_criteria",
        "stagnation_n": None,
    },
    "evaluation": {
        "next": "mapping",
        "target_mode": "prioritize",
        "auto_advance": "all_pairwise_submitted",
        "conv_modes": ["PAIRWISE", "PREMORTEM"],
        "silent_generation": False,
        "devil_active": True,
        "devil_framework": "scamper_evaluation",
        "stagnation_n": 8,
    },
    "mapping": {
        "next": None,
        "target_mode": "prioritize",
        "auto_advance": "report_generated",
        "conv_modes": [],
        "silent_generation": False,
        "devil_active": True,
        "devil_framework": "premortem_inversion",
        "on_open": ["devil_stress_test", "rapporteur_final_report"],
    },
}


def advance_phase(session: SessionState) -> Optional[str]:
    """Advance the session to the next phase based on PHASE_CONFIG.

    Args:
        session: The current session state.

    Returns:
        The new phase name if advanced, else None.
    """
    current = session["phase"]
    config = PHASE_CONFIG.get(current)
    if not config:
        return None
    next_phase = config.get("next")
    if next_phase:
        session["phase"] = next_phase  # type: ignore[assignment]
        # Additional logic for setting phase timestamps would go here.
    return next_phase