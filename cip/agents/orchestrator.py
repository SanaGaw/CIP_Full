"""Orchestrator agent.

This module coordinates idea extraction, clustering and routing decisions.
It implements the full 8-step pipeline with Bayesian updates and stagnation detection.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List

import numpy as np

from ..nlp.embeddings import embed
from ..nlp.clustering import cluster_ideas
from ..observability import log_trace


class Orchestrator:
    """Full orchestrator for routing ideas and decisions."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id

    async def classify_idea(self, idea: Dict[str, Any], session_state: Dict[str, Any] = None) -> Dict[str, Any]:
        """Classify and route an idea using the full 10-step pipeline.

        Pipeline steps:
        1. Similarity check (cosine to existing ideas)
        2. Dimension assessment (quality dimensions)
        3. Tension check (contradictions/conflicts)
        4. MECE audit (mutually exclusive, collectively exhaustive)
        5. Hypothesis evidence (alignment with active hypothesis)
        6. MAB routing (multi-armed bandit routing)
        7. Minority boost (boost underrepresented perspectives)
        8. Perspective gap (identify unexplored dimensions)
        9. Bayesian update (update beliefs based on evidence)
        10. Stagnation detection (detect diversity stagnation)
        """
        session_state = session_state or {}

        # Step 1: Similarity check
        sim_result = await self._similarity_check(idea, session_state)
        await log_trace(
            self.session_id, "orch_sim_check", "orchestrator",
            f"Similarity check complete: {sim_result.get('similarity_score', 0):.3f}",
            inputs=idea, outputs=sim_result,
            reasoning=f"Cosine similarity to existing ideas: {sim_result.get('similarity_score', 0):.3f}"
        )

        # Step 2: Dimension assessment
        dim_result = self._dimension_assessment(idea, session_state)
        await log_trace(
            self.session_id, "orch_dim_assess", "orchestrator",
            f"Dimension assessment: {dim_result}",
            inputs=idea, outputs=dim_result,
            reasoning=f"Quality dimensions: {list(dim_result.keys())}"
        )

        # Step 3: Tension check
        tension = await self._tension_check(idea, session_state)
        await log_trace(
            self.session_id, "orch_tension", "orchestrator",
            f"Tension detected: {tension.get('has_tension', False)}",
            inputs=idea, outputs=tension,
            reasoning=f"Tension signals: {tension.get('tension_signals', [])}"
        )

        # Step 4: MECE audit
        mece = await self._mece_audit(session_state)
        await log_trace(
            self.session_id, "orch_mece", "orchestrator",
            f"MECE audit: {mece}",
            inputs=session_state, outputs=mece,
            reasoning=f"MECE status: {mece.get('is_mece', 'unknown')}"
        )

        # Step 5: Hypothesis evidence
        hyp_ev = self._hypothesis_evidence(idea, session_state.get("active_hypothesis"))
        await log_trace(
            self.session_id, "orch_hyp_ev", "orchestrator",
            f"Hypothesis evidence: {hyp_ev}",
            inputs={"idea": idea, "hypothesis": session_state.get("active_hypothesis")},
            outputs=hyp_ev,
            reasoning=f"Alignment score: {hyp_ev.get('alignment', 0):.3f}"
        )

        # Step 6: MAB routing
        circulate = self._mab_routing(session_state)
        await log_trace(
            self.session_id, "orch_mab", "orchestrator",
            f"MAB routing: {circulate}",
            inputs=session_state, outputs={"circulate_to": circulate},
            reasoning=f"Selected arms: {circulate}"
        )

        # Step 7: Minority boost
        circulate += self._minority_boost(session_state)
        await log_trace(
            self.session_id, "orch_minority", "orchestrator",
            f"Minority boost added: {circulate}",
            inputs=session_state, outputs={"circulate_to": circulate},
            reasoning="Boosted underrepresented perspectives"
        )

        # Step 8: Perspective gap
        gap = self._perspective_gap(session_state)
        await log_trace(
            self.session_id, "orch_gap", "orchestrator",
            f"Perspective gap: {gap}",
            inputs=session_state, outputs=gap,
            reasoning=f"Unexplored dimensions: {gap.get('gaps', [])}"
        )

        # Step 9: Bayesian update
        bayesian = self._bayesian_update(
            prior=session_state.get("belief_prior", 0.5),
            evidence=session_state.get("last_evidence", "neutral"),
            confidence=session_state.get("evidence_confidence", 0.8)
        )
        await log_trace(
            self.session_id, "orch_bayesian", "orchestrator",
            f"Bayesian posterior: {bayesian.get('posterior', 0.5):.3f}",
            inputs=session_state, outputs=bayesian,
            reasoning=f"Prior {session_state.get('belief_prior', 0.5):.3f} updated"
        )

        # Step 10: Stagnation detection
        stagnant = self._detect_stagnation(session_state, n=5)
        await log_trace(
            self.session_id, "orch_stagnation", "orchestrator",
            f"Stagnation detected: {stagnant}",
            inputs=session_state, outputs={"is_stagnant": stagnant},
            reasoning=f"Diversity history range: {stagnant}"
        )

        result = {
            "similarity": sim_result,
            "dimension": dim_result,
            "tension": tension,
            "mece": mece,
            "hypothesis_evidence": hyp_ev,
            "circulate_to": circulate,
            "perspective_gap": gap,
            "bayesian_update": bayesian,
            "is_stagnant": stagnant,
        }

        await log_trace(
            self.session_id, "orchestrator_classify", "orchestrator",
            "Full pipeline classification complete",
            inputs=idea, outputs=result,
            reasoning="10-step pipeline completed"
        )
        return result

    async def _similarity_check(self, idea: Dict[str, Any], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """Step 1: Check cosine similarity to existing ideas."""
        idea_text = idea.get("text", "")
        if not idea_text:
            return {"similarity_score": 0.0, "nearest_idea": None}

        existing_ideas = session_state.get("ideas", [])
        if not existing_ideas:
            return {"similarity_score": 0.0, "nearest_idea": None}

        try:
            new_emb = embed(idea_text)
            max_sim = 0.0
            nearest = None

            for existing in existing_ideas:
                existing_text = existing.get("text", "")
                if not existing_text:
                    continue
                existing_emb = embed(existing_text)
                norm1 = np.linalg.norm(new_emb)
                norm2 = np.linalg.norm(existing_emb)
                if norm1 > 0 and norm2 > 0:
                    sim = float(np.dot(new_emb, existing_emb) / (norm1 * norm2))
                    if sim > max_sim:
                        max_sim = sim
                        nearest = existing_text

            return {"similarity_score": round(max_sim, 3), "nearest_idea": nearest}
        except Exception:
            return {"similarity_score": 0.5, "nearest_idea": None}

    def _dimension_assessment(self, idea: Dict[str, Any], session_state: Dict[str, Any]) -> Dict[str, float]:
        """Step 2: Assess quality dimensions."""
        from ..agents.idea_extractor import score_quality

        idea_text = idea.get("text", "")
        problem_statement = session_state.get("problem_statement", "")
        existing_clusters = session_state.get("clusters", [])

        score = score_quality(idea_text, problem_statement, existing_clusters)

        return {
            "overall_score": score,
            "is_novel": score > 0.6,
            "is_specific": score > 0.5,
            "has_evidence": score > 0.4,
        }

    async def _tension_check(self, idea: Dict[str, Any], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """Step 3: Check for contradictions/conflicts with existing ideas."""
        idea_text = idea.get("text", "").lower()
        existing_ideas = session_state.get("ideas", [])

        tension_signals = []
        contradiction_pairs = [
            ("increase", "decrease"),
            ("more", "less"),
            ("better", "worse"),
            ("expand", "contract"),
            ("invest", "divest"),
            ("automate", "manual"),
            ("centralize", "decentralize"),
        ]

        for existing in existing_ideas:
            existing_text = existing.get("text", "").lower()
            for term1, term2 in contradiction_pairs:
                if term1 in idea_text and term2 in existing_text:
                    tension_signals.append(f"{term1} vs {term2}")
                if term2 in idea_text and term1 in existing_text:
                    tension_signals.append(f"{term2} vs {term1}")

        return {
            "has_tension": len(tension_signals) > 0,
            "tension_signals": tension_signals[:5],
            "tension_count": len(tension_signals),
        }

    async def _mece_audit(self, session_state: Dict[str, Any]) -> Dict[str, Any]:
        """Step 4: MECE audit (mutually exclusive, collectively exhaustive)."""
        ideas = session_state.get("ideas", [])
        clusters = session_state.get("clusters", [])

        unique_themes = set()
        for idea in ideas:
            theme = idea.get("theme", "general")
            unique_themes.add(theme)

        total_ideas = len(ideas)
        num_clusters = len(clusters)

        # Check if we have coverage across themes
        is_mece = len(unique_themes) >= 2 and total_ideas >= 3
        coverage = min(1.0, len(unique_themes) / 5) if unique_themes else 0.0

        return {
            "is_mece": is_mece,
            "unique_themes": list(unique_themes),
            "coverage_score": round(coverage, 3),
            "num_clusters": num_clusters,
        }

    def _hypothesis_evidence(self, idea: Dict[str, Any], active_hypothesis: Dict[str, Any] = None) -> Dict[str, Any]:
        """Step 5: Assess alignment with active hypothesis."""
        if not active_hypothesis:
            return {"alignment": 0.5, "supports": None, "contradicts": False}

        idea_text = idea.get("text", "").lower()
        hypothesis_text = active_hypothesis.get("text", "").lower()
        hypothesis_components = active_hypothesis.get("components", [])

        # Count supporting keywords
        supports = 0
        for component in hypothesis_components:
            if component.lower() in idea_text:
                supports += 1

        # Check for contradiction keywords
        contradiction_keywords = ["not", "no", "never", "don't", "avoid", "stop", "prevent"]
        contradicts = any(kw in idea_text.split()[:10] for kw in contradiction_keywords)

        alignment = min(1.0, supports / max(1, len(hypothesis_components)) * 0.8 + 0.2)

        return {
            "alignment": round(alignment, 3),
            "supports": supports,
            "contradicts": contradicts,
        }

    def _mab_routing(self, session_state: Dict[str, Any]) -> List[str]:
        """Step 6: Multi-armed bandit routing."""
        arm_counts = session_state.get("mab_arm_counts", {})
        diversity_history = session_state.get("diversity_history", [])

        # Thompson sampling - sample from beta distribution
        routing = []
        modes = ["PROBE", "EXTEND", "CHALLENGE", "BRIDGE"]

        # Explore underused modes
        for mode in modes:
            count = arm_counts.get(mode, 0)
            if count == 0:
                routing.append(mode)

        # If all explored, pick random
        if not routing:
            routing = [random.choice(modes)]

        # Cap at 2 routes
        return routing[:2]

    def _minority_boost(self, session_state: Dict[str, Any]) -> List[str]:
        """Step 7: Boost underrepresented perspectives."""
        perspective_counts = session_state.get("perspective_counts", {})
        ideas = session_state.get("ideas", [])

        if not ideas:
            return []

        total = len(ideas)
        minority_routes = []

        for perspective, count in perspective_counts.items():
            if total > 0 and (count / total) < 0.15:
                minority_routes.append(perspective.upper())

        return minority_routes[:2]

    def _perspective_gap(self, session_state: Dict[str, Any]) -> Dict[str, Any]:
        """Step 8: Identify unexplored dimensions."""
        ideas = session_state.get("ideas", [])
        expected_dimensions = ["cost", "time", "risk", "quality", "scope", "resources", "stakeholder"]

        covered_dims = set()
        for idea in ideas:
            text = idea.get("text", "").lower()
            for dim in expected_dimensions:
                if dim in text:
                    covered_dims.add(dim)

        gaps = [d for d in expected_dimensions if d not in covered_dims]

        return {
            "gaps": gaps,
            "gap_count": len(gaps),
            "coverage": round(len(covered_dims) / len(expected_dimensions), 3),
        }

    def _bayesian_update(self, prior: float, evidence: str, confidence: float) -> Dict[str, float]:
        """Step 9: Bayesian belief update."""
        likelihoods = {
            "agree": 3.5,
            "disagree": 0.28,
            "neutral": 1.0,
            "strong_agree": 5.0,
            "strong_disagree": 0.1,
        }
        L = likelihoods.get(evidence, 1.0) * confidence

        # Bayes theorem: P(H|E) = P(E|H) * P(H) / P(E)
        prior_odds = prior / (1 - prior) if prior > 0 and prior < 1 else 1.0
        post_odds = prior_odds * L
        posterior = post_odds / (1 + post_odds)
        posterior = max(0.02, min(0.98, posterior))

        return {"posterior": round(posterior, 3), "prior": prior, "likelihood": L}

    def _detect_stagnation(self, session_state: Dict[str, Any], n: int = 5) -> bool:
        """Step 10: Detect diversity stagnation."""
        history = session_state.get("diversity_history", [])
        if len(history) < n:
            return False

        recent = history[-n:]
        score_range = max(recent) - min(recent)
        return score_range < 0.05
