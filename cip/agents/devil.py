"""Devil's advocate agent.

This agent injects contrarian perspectives to challenge the group's assumptions
and surface unseen risks. It implements 4 phase frameworks and a stress_test method.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List

from ..observability import log_trace


class DevilAgent:
    """Devil's advocate implementation with phase frameworks and stress testing."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id

    # Phase frameworks for different stages
    PHASE_FRAMEWORKS = {
        "clarification": {
            "name": "Clarification Phase Challenge",
            "questions": [
                "What if our understanding of the problem is fundamentally wrong?",
                "Are we solving the right problem or just the visible one?",
                "Who benefits most from our current problem framing?",
            ],
            "stress_dimensions": ["scope", "assumptions", "stakeholder_analysis"],
        },
        "ideation": {
            "name": "Ideation Phase Challenge",
            "questions": [
                "What ideas are we avoiding because they're uncomfortable?",
                "What solutions have failed in similar contexts and why?",
                "What would a competitor do that's the opposite of our direction?",
            ],
            "stress_dimensions": ["creativity", "precedent", "contrarian"],
        },
        "evaluation": {
            "name": "Evaluation Phase Challenge",
            "questions": [
                "What evidence would change our minds?",
                "Are we overweighting recent data over historical patterns?",
                "What are we assuming about uncertainty that might be wrong?",
            ],
            "stress_dimensions": ["evidence", "bias", "uncertainty"],
        },
        "refinement": {
            "name": "Refinement Phase Challenge",
            "questions": [
                "What could go catastrophically wrong?",
                "What assumptions would break our solution?",
                "What do we believe that's actually slowing us down?",
            ],
            "stress_dimensions": ["risk", "assumptions", "failure_modes"],
        },
    }

    async def trigger(self, phase: str) -> Dict[str, Any]:
        """Trigger the devil agent for a given phase.

        Args:
            phase: The current session phase (clarification, ideation, evaluation, refinement).

        Returns:
            A dict with generated challenges and stress tests.
        """
        framework = self.PHASE_FRAMEWORKS.get(phase, self.PHASE_FRAMEWORKS["clarification"])

        challenges = self._generate_challenges(framework)
        stress_result = await self.stress_test(phase)

        await log_trace(
            self.session_id,
            "devil_trigger",
            "devil",
            f"Devil triggered in phase {phase}",
            inputs={"phase": phase},
            outputs={"challenges": challenges, "stress_result": stress_result},
            reasoning=f"Phase framework: {framework['name']}",
        )

        return {
            "phase": phase,
            "framework_name": framework["name"],
            "challenges": challenges,
            "stress_result": stress_result,
            "stress_dimensions": framework["stress_dimensions"],
        }

    def _generate_challenges(self, framework: Dict[str, Any]) -> List[str]:
        """Generate devil's advocate challenges based on framework."""
        return framework.get("questions", [])

    async def stress_test(self, phase: str) -> Dict[str, Any]:
        """Perform stress testing on the current session state.

        Args:
            phase: The current session phase.

        Returns:
            Dictionary with stress test results including failure modes and edge cases.
        """
        stress_scenarios = self._build_stress_scenarios(phase)
        weak_signals = self._detect_weak_signals()
        failure_modes = self._identify_failure_modes()

        result = {
            "scenarios_tested": len(stress_scenarios),
            "scenarios": stress_scenarios,
            "weak_signals_detected": weak_signals,
            "critical_failure_modes": failure_modes,
            "resilience_score": self._calculate_resilience_score(stress_scenarios),
        }

        await log_trace(
            self.session_id,
            "devil_stress_test",
            "devil",
            f"Stress test completed for phase {phase}",
            inputs={"phase": phase},
            outputs=result,
            reasoning="Stress test completed",
        )

        return result

    def _build_stress_scenarios(self, phase: str) -> List[Dict[str, Any]]:
        """Build stress test scenarios based on phase."""
        base_scenarios = [
            {
                "scenario": "Resource constraints increase by 50%",
                "impact": "high",
                "probability": "medium",
                "mitigation": "Identify minimum viable scope",
            },
            {
                "scenario": "Key stakeholder changes direction",
                "impact": "high",
                "probability": "medium",
                "mitigation": "Build multiple alignment paths",
            },
            {
                "scenario": "Timeline pressure doubles",
                "impact": "medium",
                "probability": "high",
                "mitigation": "Prioritize core functionality",
            },
        ]

        phase_scenarios = {
            "clarification": base_scenarios[:2] + [{
                "scenario": "Problem definition shifts mid-session",
                "impact": "critical",
                "probability": "low",
                "mitigation": "Lock problem statement early with sign-off",
            }],
            "ideation": base_scenarios[:2] + [{
                "scenario": "Creative energy depletes early",
                "impact": "medium",
                "probability": "high",
                "mitigation": "Vary facilitation techniques",
            }],
            "evaluation": base_scenarios[:2] + [{
                "scenario": "Consensus forms around suboptimal choice",
                "impact": "high",
                "probability": "medium",
                "mitigation": "Challenge winners explicitly",
            }],
            "refinement": base_scenarios[:2] + [{
                "scenario": "Implementation reveals hidden complexity",
                "impact": "critical",
                "probability": "high",
                "mitigation": "Reserve 30% buffer for unknowns",
            }],
        }

        return phase_scenarios.get(phase, base_scenarios)

    def _detect_weak_signals(self) -> List[str]:
        """Detect weak signals that might indicate emerging issues."""
        return [
            "Low engagement on critical path items",
            "Recurring deferrals on technical decisions",
            "Stakeholder silence during risk discussions",
            "Pattern matching without evidence",
        ]

    def _identify_failure_modes(self) -> List[str]:
        """Identify critical failure modes."""
        return [
            "Confirmation bias in idea selection",
            "Groupthink during consensus formation",
            "Overconfidence in risk assessment",
            "Sunk cost fallacy in continued investment",
        ]

    def _calculate_resilience_score(self, scenarios: List[Dict]) -> float:
        """Calculate resilience score based on scenario mitigations."""
        if not scenarios:
            return 0.0

        scored = 0
        for s in scenarios:
            impact = {"critical": 3, "high": 2, "medium": 1}.get(s.get("impact", "medium"), 1)
            has_mitigation = 1 if s.get("mitigation") else 0
            scored += impact * has_mitigation

        max_score = sum({"critical": 3, "high": 2, "medium": 1}.get(s.get("impact", "medium"), 1) for s in scenarios)
        return round(scored / max_score if max_score > 0 else 0, 2)

    async def challenge_idea(self, idea: Dict[str, Any]) -> Dict[str, Any]:
        """Challenge a specific idea with devil's advocate perspective.

        Args:
            idea: The idea dictionary to challenge.

        Returns:
            Dictionary with challenge questions and alternative perspectives.
        """
        idea_text = idea.get("text", "")

        challenges = [
            f"What if '{idea_text}' is based on flawed assumptions?",
            f"What evidence would disprove '{idea_text}'?",
            f"Who might be harmed by '{idea_text}'?",
            f"What would the opposite approach look like?",
        ]

        result = {
            "original_idea": idea_text,
            "challenge_questions": challenges,
            "alternative_perspectives": self._generate_alternatives(idea),
            "risk_factors": self._assess_risk_factors(idea),
        }

        await log_trace(
            self.session_id,
            "devil_challenge_idea",
            "devil",
            f"Idea challenged: {idea_text[:50]}...",
            inputs={"idea": idea},
            outputs=result,
            reasoning="Devil's advocate challenge applied",
        )

        return result

    def _generate_alternatives(self, idea: Dict[str, Any]) -> List[str]:
        """Generate alternative perspectives to the idea."""
        return [
            "The opposite approach might reduce unintended consequences",
            "Simpler solutions might achieve similar outcomes",
            "Deferring might allow better information to emerge",
            "Incremental approach might reveal issues earlier",
        ]

    def _assess_risk_factors(self, idea: Dict[str, Any]) -> List[str]:
        """Assess risk factors for an idea."""
        return [
            "Implementation complexity",
            "Stakeholder alignment gaps",
            "Uncertainty in success metrics",
            "Dependencies on external factors",
        ]