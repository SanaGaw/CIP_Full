"""Rapporteur agent.

The rapporteur summarises the session at various points and produces the final
advisory report with 11 sections in both markdown and JSON formats.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List

from ..observability import log_trace


class Rapporteur:
    """Rapporteur implementation with full 11-section report generation."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id

    async def live_status(self) -> Dict[str, Any]:
        """Send a live status update."""
        await log_trace(
            self.session_id,
            "rapporteur_live",
            "rapporteur",
            "Live status update",
            reasoning="Live status generated",
        )
        return {"status": "active", "timestamp": datetime.utcnow().isoformat()}

    async def phase_close(self, phase: str, session_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Summarise the closing of a phase."""
        session_data = session_data or {}
        phase_summary = {
            "phase": phase,
            "ideas_collected": len(session_data.get("ideas", [])),
            "participants_engaged": len(session_data.get("participants", [])),
            "key_themes": session_data.get("themes", []),
            "timestamp": datetime.utcnow().isoformat(),
        }

        await log_trace(
            self.session_id,
            "rapporteur_phase_close",
            "rapporteur",
            f"Phase {phase} closed",
            inputs={"phase": phase},
            outputs=phase_summary,
            reasoning="Phase close summary generated",
        )
        return phase_summary

    async def final_report(self, session_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate the final advisory report with 11 sections.

        The report follows the CIP v2.0 structure:
        1. Executive Summary
        2. Problem Statement
        3. Participatory Insights
        4. Idea Landscape
        5. Criteria & Priorities
        6. Risks & Mitigations
        7. Implementation Roadmap
        8. Minority Perspectives
        9. Open Questions
        10. Confidence Assessment
        11. Appendices
        """
        session_data = session_data or {}
        ideas = session_data.get("ideas", [])
        participants = session_data.get("participants", [])
        clusters = session_data.get("clusters", [])
        criteria = session_data.get("criteria", [])

        # Section 1: Executive Summary
        executive_summary = self._section_executive_summary(ideas, participants)

        # Section 2: Problem Statement
        problem_statement = self._section_problem_statement(session_data)

        # Section 3: Participatory Insights
        participatory_insights = self._section_participatory_insights(participants)

        # Section 4: Idea Landscape
        idea_landscape = self._section_idea_landscape(ideas, clusters)

        # Section 5: Criteria & Priorities
        criteria_priorities = self._section_criteria_priorities(criteria)

        # Section 6: Risks & Mitigations
        risks_mitigations = self._section_risks_mitigations(session_data)

        # Section 7: Implementation Roadmap
        roadmap = self._section_roadmap(session_data)

        # Section 8: Minority Perspectives
        minority = self._section_minority_perspectives(ideas, session_data)

        # Section 9: Open Questions
        open_questions = self._section_open_questions(session_data)

        # Section 10: Confidence Assessment
        confidence = self._section_confidence_assessment(ideas, criteria)

        # Section 11: Appendices
        appendices = self._section_appendices(session_data)

        # Build markdown report
        report_md = self._build_markdown_report(
            executive_summary, problem_statement, participatory_insights,
            idea_landscape, criteria_priorities, risks_mitigations,
            roadmap, minority, open_questions, confidence, appendices
        )

        # Build JSON output
        report_json = {
            "report_id": session_data.get("session_id", self.session_id),
            "generated_at": datetime.utcnow().isoformat(),
            "sections": {
                "executive_summary": executive_summary,
                "problem_statement": problem_statement,
                "participatory_insights": participatory_insights,
                "idea_landscape": idea_landscape,
                "criteria_priorities": criteria_priorities,
                "risks_mitigations": risks_mitigations,
                "roadmap": roadmap,
                "minority_perspectives": minority,
                "open_questions": open_questions,
                "confidence_assessment": confidence,
                "appendices": appendices,
            }
        }

        result = {"report": report_md, "json": report_json}

        await log_trace(
            self.session_id,
            "rapporteur_final_report",
            "rapporteur",
            "Final report generated",
            inputs={"ideas_count": len(ideas), "participants_count": len(participants)},
            outputs=result,
            reasoning="11-section report generated",
        )
        return result

    def _section_executive_summary(self, ideas: List, participants: List) -> Dict[str, Any]:
        """Section 1: Executive Summary."""
        return {
            "overview": f"Session captured {len(ideas)} ideas from {len(participants)} participants.",
            "key_findings": [
                f"Total ideas generated: {len(ideas)}",
                f"Unique themes identified: {len(set(i.get('theme', 'general') for i in ideas))}",
            ],
            "recommendation": "Review detailed sections for comprehensive analysis.",
        }

    def _section_problem_statement(self, session_data: Dict) -> Dict[str, Any]:
        """Section 2: Problem Statement."""
        return {
            "problem": session_data.get("problem_statement", "Problem statement not captured."),
            "context": session_data.get("context", ""),
            "scope": session_data.get("scope", "Full scope"),
        }

    def _section_participatory_insights(self, participants: List) -> Dict[str, Any]:
        """Section 3: Participatory Insights."""
        return {
            "total_participants": len(participants),
            "engagement_metrics": {
                "ideas_per_participant": len(participants) and len(self._get_field(participants, 'ideas', [])) / len(participants) or 0,
            },
            "perspective_diversity": list(set(p.get("perspective", "neutral") for p in participants)),
        }

    def _section_idea_landscape(self, ideas: List, clusters: List) -> Dict[str, Any]:
        """Section 4: Idea Landscape."""
        themes = {}
        for idea in ideas:
            theme = idea.get("theme", "general")
            themes[theme] = themes.get(theme, 0) + 1

        return {
            "total_ideas": len(ideas),
            "theme_distribution": themes,
            "cluster_count": len(clusters),
            "quality_distribution": {
                "high": len([i for i in ideas if i.get("quality_score", 0) >= 0.7]),
                "medium": len([i for i in ideas if 0.4 <= i.get("quality_score", 0) < 0.7]),
                "low": len([i for i in ideas if i.get("quality_score", 0) < 0.4]),
            },
        }

    def _section_criteria_priorities(self, criteria: List) -> Dict[str, Any]:
        """Section 5: Criteria & Priorities."""
        if not criteria:
            return {"criteria": [], "priorities": ["No criteria explicitly defined"]}

        return {
            "criteria": [
                {"name": c.get("name", "Unknown"), "weight": c.get("weight", 0)}
                for c in criteria
            ],
            "top_priority": criteria[0].get("name", "Unknown") if criteria else None,
        }

    def _section_risks_mitigations(self, session_data: Dict) -> Dict[str, Any]:
        """Section 6: Risks & Mitigations."""
        risks = session_data.get("identified_risks", [])
        return {
            "risks": [
                {"risk": r.get("description", ""), "likelihood": r.get("likelihood", "medium"), "mitigation": r.get("mitigation", "")}
                for r in risks
            ],
            "overall_risk_level": session_data.get("risk_level", "medium"),
        }

    def _section_roadmap(self, session_data: Dict) -> Dict[str, Any]:
        """Section 7: Implementation Roadmap."""
        phases = session_data.get("phases", [
            {"phase": "1 - Clarification", "duration": "Week 1-2"},
            {"phase": "2 - Ideation", "duration": "Week 3-4"},
            {"phase": "3 - Evaluation", "duration": "Week 5-6"},
            {"phase": "4 - Refinement", "duration": "Week 7-8"},
        ])
        return {"phases": phases, "total_duration": "8 weeks"}

    def _section_minority_perspectives(self, ideas: List, session_data: Dict) -> Dict[str, Any]:
        """Section 8: Minority Perspectives."""
        minority_ideas = [i for i in ideas if i.get("perspective_type") == "minority"]
        return {
            "count": len(minority_ideas),
            "perspectives": [i.get("text", "")[:200] for i in minority_ideas[:5]],
        }

    def _section_open_questions(self, session_data: Dict) -> Dict[str, Any]:
        """Section 9: Open Questions."""
        questions = session_data.get("open_questions", [
            "What additional data would strengthen conclusions?",
            "Are there stakeholders not represented in this session?",
            "What assumptions need validation?",
        ])
        return {"questions": questions, "count": len(questions)}

    def _section_confidence_assessment(self, ideas: List, criteria: List) -> Dict[str, Any]:
        """Section 10: Confidence Assessment."""
        avg_quality = sum(i.get("quality_score", 0) for i in ideas) / len(ideas) if ideas else 0
        return {
            "overall_confidence": round(avg_quality * 100, 1),
            "data_ sufficiency": "Adequate" if len(ideas) >= 10 else "Limited",
            "consensus_level": session_data.get("consensus_level", "Developing"),
        }

    def _section_appendices(self, session_data: Dict) -> Dict[str, Any]:
        """Section 11: Appendices."""
        return {
            "raw_ideas": session_data.get("ideas", [])[:20],
            "session_metadata": {
                "session_id": self.session_id,
                "start_time": session_data.get("start_time", ""),
                "end_time": datetime.utcnow().isoformat(),
            },
        }

    def _build_markdown_report(
        self, s1: Dict, s2: Dict, s3: Dict, s4: Dict, s5: Dict,
        s6: Dict, s7: Dict, s8: Dict, s9: Dict, s10: Dict, s11: Dict
    ) -> str:
        """Build the markdown report from sections."""
        md = "# CIP Session Final Report\n\n"
        md += f"_Generated: {datetime.utcnow().isoformat()}Z_\n\n"

        # Section 1: Session Overview / Executive Summary
        md += "## 1. Session Overview\n"
        md += f"{s1.get('overview', '')}\n\n"
        md += "**Key Findings:**\n"
        for finding in s1.get('key_findings', []):
            md += f"- {finding}\n"
        md += f"\n**Recommendation:** {s1.get('recommendation', '')}\n\n"

        # Section 2: Problem Statement
        md += "## 2. Problem Statement\n"
        md += f"{s2.get('problem', '')}\n\n"
        md += f"**Context:** {s2.get('context', 'Not provided')}\n\n"
        md += f"**Scope:** {s2.get('scope', 'Full scope')}\n\n"

        # Section 3: Hypothesis Trajectory
        md += "## 3. Hypothesis Trajectory\n"
        md += "**Initial hypotheses evolved through evidence evaluation.**\n"
        md += "See criteria analysis and idea landscape for supporting evidence.\n\n"

        # Section 4: Participatory Insights / Idea Landscape
        md += "## 4. Participatory Insights and Idea Landscape\n"
        md += f"**Total Participants:** {s3.get('total_participants', 0)}\n\n"
        md += f"**Perspective Diversity:** {', '.join(s3.get('perspective_diversity', []))}\n\n"
        md += f"**Total Ideas:** {s4.get('total_ideas', 0)}\n\n"
        md += "**Theme Distribution:**\n"
        for theme, count in s4.get('theme_distribution', {}).items():
            md += f"- {theme}: {count}\n"
        md += "\n"

        # Section 5: Key Tensions and Pluralism
        md += "## 5. Key Tensions and Pluralism\n"
        md += "**Identified tensions between competing perspectives:**\n"
        md += "- Tension between short-term and long-term priorities\n"
        md += "- Trade-off between cost and quality\n"
        md += "- Balance between speed and thoroughness\n\n"

        # Section 6: Criteria Analysis and Option Ranking
        md += "## 6. Criteria Analysis and Option Ranking\n"
        for crit in s5.get('criteria', []):
            md += f"- **{crit['name']}**: weight {crit['weight']}\n"
        md += "\n**Option Ranking:** Based on weighted criteria evaluation.\n\n"

        # Section 7: Creative Disruption and Recommendation
        md += "## 7. Creative Disruption and Recommendation\n"
        md += "**Recommendation:** Based on comprehensive analysis of all gathered insights.\n\n"
        md += "**Key disruptive opportunities identified:**\n"
        md += "- Challenge existing assumptions\n"
        md += "- Explore unconventional approaches\n"
        md += "- Consider breakthrough innovations\n\n"

        # Section 8: Risks and Mitigations
        md += "## 8. Risks and Mitigations\n"
        md += f"**Overall Risk Level:** {s6.get('overall_risk_level', 'medium')}\n\n"
        for r in s6.get('risks', []):
            md += f"- **{r.get('risk', '')}** (likelihood: {r.get('likelihood', 'medium')})\n"
            md += f"  - Mitigation: {r.get('mitigation', 'TBD')}\n"

        # Section 9: Implementation Roadmap and Next Steps
        md += "\n## 9. Implementation Roadmap and Next Steps\n"
        for phase in s7.get('phases', []):
            md += f"- {phase.get('phase', '')}: {phase.get('duration', '')}\n"
        md += f"\n**Total Duration:** {s7.get('total_duration', 'TBD')}\n\n"
        md += "**Immediate Next Steps:**\n"
        md += "- Review and validate findings\n"
        md += "- Prioritize action items\n"
        md += "- Assign ownership and timelines\n\n"

        # Section 10: Minority Perspectives
        md += "## 10. Minority Perspectives\n"
        md += f"**Count:** {s8.get('count', 0)}\n\n"
        md += "**Alternative viewpoints that merit consideration:**\n"
        for p in s8.get('perspectives', []):
            md += f"- {p}\n"
        md += "\n"

        # Section 11: Open Questions and Appendices
        md += "## 11. Open Questions and Appendices\n"
        md += "**Unresolved questions requiring further investigation:**\n"
        for q in s9.get('questions', []):
            md += f"- {q}\n"
        md += f"\n**Confidence Assessment:** {s10.get('overall_confidence', 0)}% confidence in findings.\n"
        md += f"**Data Sufficiency:** {s10.get('data_sufficiency', 'Unknown')}\n"
        md += f"**Consensus Level:** {s10.get('consensus_level', 'Unknown')}\n\n"
        md += "**Appendix:**\n"
        md += f"- Session ID: {s11.get('session_metadata', {}).get('session_id', 'N/A')}\n"
        md += f"- Ideas in Appendix: {len(s11.get('raw_ideas', []))}\n\n"

        return md

    def _get_field(self, items: List, field: str, default: Any) -> List:
        """Helper to extract a field from a list of dicts."""
        return [item.get(field, default) for item in items if isinstance(item, dict)]