"""Tier definitions and provider mappings.

This module defines the provider chains for each tier and a default
mapping from task identifiers to tiers.
"""
from __future__ import annotations

TIER_PROVIDERS = {
    "T0": [],
    "T1": [
        ("gemini", "gemini-2.0-flash"),
        ("openrouter", "meta-llama/llama-3.3-70b-instruct:free"),
        ("openrouter", "deepseek/deepseek-chat:free"),
    ],
    "T2": [
        ("groq", "llama-3.3-70b-versatile"),
        ("openrouter", "deepseek/deepseek-chat"),
        ("gemini", "gemini-2.0-flash"),
    ],
    "T3": [
        ("anthropic", "claude-sonnet-4-5-20250514"),
        ("openrouter", "anthropic/claude-sonnet-4-5-20250514"),
        ("groq", "llama-3.3-70b-versatile"),
    ],
}


DEFAULT_TIER_MAP = {
    # Conversation Agent
    "conv.LISTEN": "T1",
    "conv.NARRATE": "T1",
    "conv.REFLECT": "T1",
    "conv.BRIDGE": "T1",
    "conv.RECALL": "T1",
    "conv.PREMORTEM": "T1",
    "conv.CRITERIA": "T1",
    "conv.PAIRWISE": "T1",
    # Orchestrator
    "orch.classify": "T0",
    "orch.dimension": "T0",
    "orch.mece_audit": "T1",
    "orch.tension_check": "T1",
    "orch.cluster_label": "T1",
    "orch.bayesian_update": "T0",
    "orch.mab_routing": "T0",
    "orch.minority_boost": "T0",
    "orch.perspective_gap": "T0",
    "orch.stagnation": "T0",
    "orch.hypothesis_evidence": "T0",
    # Specialized agents
    "pc.synthesize": "T2",
    "hyp.generate": "T2",
    # Devil's Advocate
    "devil.divergence": "T1",
    "devil.exploration": "T1",
    "devil.criteria": "T1",
    "devil.evaluation": "T1",
    "devil.stress_test": "T2",
    # Rapporteur
    "rapporteur.live": "T0",
    "rapporteur.phase_close": "T1",
    "rapporteur.final_report": "T2",
    # Engines (all T0)
    "criteria.ahp": "T0",
    "criteria.polarization": "T0",
    "condorcet.rank": "T0",
    "condorcet.cycle": "T0",
    "bridge.compute": "T0",
    "extractor.parse": "T0",
    "extractor.quality": "T0",
    "bias.detect": "T0",
    "nlp.embed": "T0",
    "nlp.cluster": "T0",
    "nlp.diversity": "T0",
    "nlp.language": "T0",
}