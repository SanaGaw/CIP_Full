"""Global application state and typed data contracts.

This module defines the typed dictionaries used throughout the application to
represent user profiles, idea clusters, option candidates and session state.
It also maintains global references to the current session and connection
manager.
"""
from __future__ import annotations

from typing import Dict, List, Optional, TypedDict, Literal


class UserProfile(TypedDict):
    user_id: str
    style: str
    engagement: str
    perspective_role: str
    language: str
    fluency: str
    ideas: List[str]
    assumptions: List[str]
    shifts: List[str]
    stance_history: List[dict]
    reaction_log: List[dict]
    surprise_scores: List[float]
    quality_scores: List[float]
    narrative_elements: dict
    ahp_weights: dict
    pairwise_votes: List[dict]
    premortem_contributions: List[dict]
    bias_flags: List[dict]
    conv_history: List[dict]


class IdeaCluster(TypedDict):
    cluster_id: str
    label: str
    ideas: List[str]
    count: int
    author_ids: List[str]
    dimension: str
    tension_with: List[str]
    phase_created: str
    circulation_count: int
    last_circulated_at: Optional[str]
    option_archetype: Optional[str]
    hypothesis_evidence: str
    quality_weighted_count: float
    sentiment_trajectory: str
    bandit_reward: float
    bandit_pulls: int
    mece_flags: List[str]


class OptionCandidate(TypedDict):
    option_id: str
    label: str
    archetype: str
    source_clusters: List[str]
    supporting_stances: int
    opposing_stances: int
    weighted_score: float
    condorcet_wins: int
    polarization_index: float
    premortem_risks: List[str]
    hypothesis_alignment: str


class SessionState(TypedDict):
    session_id: str
    topic: str
    expected_participants: int
    expected_duration_minutes: int
    phase: Literal[
        "onboarding",
        "define",
        "divergence",
        "exploration",
        "criteria",
        "evaluation",
        "mapping",
    ]
    target_mode: Optional[str]
    started_at: str
    phase_started_at: str
    problem_statement: Optional[str]
    active_hypothesis: Optional[str]
    participant_count: int
    perspective_coverage: dict
    stagnation_counter: int
    diversity_score: float
    disruption_level: int
    idea_pool: Dict[str, IdeaCluster]
    unique_dimensions: List[str]
    borderline_log: List[dict]
    option_pool: List[OptionCandidate]
    condorcet_matrix: dict
    criteria_list: List[dict]
    group_ahp_weights: dict
    criteria_polarization: dict
    session_quality_score: float
    event_log: List[dict]
    users: Dict[str, UserProfile]
    silent_generation_active: bool
    silent_generation_until: Optional[str]


# Global references to the current session and connection manager. These are
# initialised by the application lifecycle.
current_session: Optional[SessionState] = None
connection_manager = None  # this will be set to a ConnectionManager instance