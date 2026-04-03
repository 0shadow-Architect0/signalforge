"""Red Team Builder - Constructs the strongest possible case AGAINST your thesis.

Innovation: Instead of asking "is my thesis right?", this asks "what's the 
strongest argument that my thesis is WRONG?" and builds it with the same 
rigor and evidence chains that the main analysis uses.

This is NOT a simple "list of cons". It's a structured, evidence-backed 
counter-argument that treats your thesis the way a hostile investor would 
during due diligence.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


RED_TEAM_SYSTEM_PROMPT = """You are a world-class strategic adversary. Your job is to build the STRONGEST possible case AGAINST a thesis.

You are not trying to be mean or contrarian for its own sake. You are a rigorous, evidence-based thinker who finds the genuine weaknesses, blind spots, and failure modes in strategic arguments.

For the given thesis and its supporting evidence, produce a structured counter-analysis:

{
  "anti_thesis": "The strongest one-line argument against this thesis",
  "anti_thesis_confidence": 0.0-1.0,
  "load_bearing_assumptions": [
    {
      "assumption": "What must be true for the thesis to hold",
      "failure_probability": "low/medium/high",
      "historical_failure_rate": "How often similar assumptions fail",
      "what_would_expose_it": "Specific test or signal that would reveal the assumption is wrong"
    }
  ],
  "counter_evidence_search": [
    "Specific search queries that would find disconfirming evidence",
    "Types of sources to look for",
    "Specific metrics or data points to track"
  ],
  "failure_modes": [
    {
      "mode": "Name of this failure mode",
      "description": "How the thesis could fail this way",
      "early_warning_signals": ["What to watch for"],
      "probability": "low/medium/high",
      "impact": "low/medium/high"
    }
  ],
  "steel_man_opposition": "The most generous and rigorous version of the argument against this thesis",
  "market_concerns": ["What the market knows that contradicts this thesis"],
  "timing_risks": ["Why now might be the wrong time"],
  "execution_traps": ["Ways the execution could fail even if the thesis is correct"],
  "overall_vulnerability_score": 0.0-1.0
}

Be intellectually honest. Don't straw-man the thesis. Build the REAL strongest opposition.
If the thesis is genuinely strong, say so. Your job is truth-seeking, not destruction."""

RED_TEAM_USER_TEMPLATE = """Build the adversarial case against this thesis:

Thesis: {thesis_name}
One-line: {one_line_thesis}
Strategic Wedge: {wedge_statement}

Supporting Evidence:
{evidence_summary}

Current Scores:
- Whitespace: {whitespace_score}
- Novelty: {novelty}
- Urgency: {urgency}
- Founder Fit: {founder_fit}
- Buildability: {buildability}
- Strategic Leverage: {strategic_leverage}

Contradictions Found:
{contradictions}

Build the strongest possible case AGAINST this thesis."""


class RedTeamBuilder:
    """Builds and maintains adversarial counter-arguments against theses.
    
    Features:
    - Steel-man opposition (strongest counter-argument, not straw-man)
    - Load-bearing assumption identification
    - Failure mode analysis with early warning signals
    - Counter-evidence search queries
    - Vulnerability scoring
    """
    
    def __init__(self, provider: Any) -> None:
        self.provider = provider
    
    def build_red_team(
        self,
        thesis_payload: dict,
        evidence_summary: str = "",
    ) -> dict | None:
        """Build a complete adversarial analysis against a thesis.
        
        Returns None if provider unavailable (graceful degradation).
        """
        if not self.provider or not self.provider.available():
            return self._deterministic_red_team(thesis_payload)
        
        # Gather thesis data
        whitespace = thesis_payload.get("whitespace", {})
        opportunity = thesis_payload.get("opportunity", {}).get("scores", {})
        contradictions = thesis_payload.get("contradictions", {})
        
        contradiction_lines = []
        for c in contradictions.get("contradictions", []):
            contradiction_lines.append(f"- {c}")
        
        user_prompt = RED_TEAM_USER_TEMPLATE.format(
            thesis_name=thesis_payload.get("name", "Unnamed"),
            one_line_thesis=thesis_payload.get("one_line_thesis", "N/A"),
            wedge_statement=whitespace.get("wedge_statement", "N/A"),
            evidence_summary=evidence_summary or "See supporting sources for details.",
            whitespace_score=whitespace.get("whitespace_score", 0),
            novelty=opportunity.get("novelty", 0),
            urgency=opportunity.get("urgency", 0),
            founder_fit=opportunity.get("founder_fit", 0),
            buildability=opportunity.get("buildability", 0),
            strategic_leverage=opportunity.get("strategic_leverage", 0),
            contradictions="\n".join(contradiction_lines) or "- None detected",
        )
        
        result = self.provider.complete_structured(
            system=RED_TEAM_SYSTEM_PROMPT,
            user=user_prompt,
            expected_keys=["anti_thesis", "load_bearing_assumptions", "failure_modes"],
            temperature=0.4,
        )
        
        if result is None:
            return self._deterministic_red_team(thesis_payload)
        
        return {
            "thesis_id": thesis_payload.get("id"),
            "anti_thesis": result.get("anti_thesis"),
            "anti_thesis_confidence": result.get("anti_thesis_confidence", 0.5),
            "load_bearing_assumptions": result.get("load_bearing_assumptions", []),
            "counter_evidence_search": result.get("counter_evidence_search", []),
            "failure_modes": result.get("failure_modes", []),
            "steel_man_opposition": result.get("steel_man_opposition"),
            "market_concerns": result.get("market_concerns", []),
            "timing_risks": result.get("timing_risks", []),
            "execution_traps": result.get("execution_traps", []),
            "overall_vulnerability_score": result.get("overall_vulnerability_score", 0.5),
            "source": "llm" if self.provider.available() else "deterministic",
        }
    
    def _deterministic_red_team(self, thesis_payload: dict) -> dict:
        """Fallback: deterministic red team analysis without LLM.
        
        Uses heuristics to identify weaknesses based on score patterns.
        """
        whitespace = thesis_payload.get("whitespace", {})
        opportunity = thesis_payload.get("opportunity", {}).get("scores", {})
        contradictions = thesis_payload.get("contradictions", {})
        comparison = thesis_payload.get("comparison", {})
        
        # Identify weakness signals
        vulnerability_signals = []
        
        novelty = opportunity.get("novelty", 7.0)
        if novelty < 7.5:
            vulnerability_signals.append("novelty is below threshold - the space may already be occupied")
        
        urgency = opportunity.get("urgency", 7.0)
        if urgency < 7.0:
            vulnerability_signals.append("urgency is low - the timing window may be closing or not yet open")
        
        founder_fit = opportunity.get("founder_fit", 7.0)
        if founder_fit < 7.0:
            vulnerability_signals.append("founder fit is weak - the thesis may not align with actual capabilities")
        
        buildability = opportunity.get("buildability", 7.0)
        if buildability < 7.0:
            vulnerability_signals.append("buildability is low - execution may be harder than the strategic case suggests")
        
        whitespace_score = float(whitespace.get("whitespace_score", 0) or 0)
        if whitespace_score < 7.5:
            vulnerability_signals.append("whitespace is narrow - the opportunity gap may be closing")
        
        contradiction_severity = contradictions.get("severity", "low")
        if contradiction_severity == "high":
            vulnerability_signals.append("contradiction severity is HIGH - the evidence base is internally conflicted")
        
        overlap = float(comparison.get("overlap_strength", 0) or 0)
        if overlap > 0.4:
            vulnerability_signals.append("overlap is high - the category may be getting crowded")
        
        # Generate load-bearing assumptions from analysis
        assumptions = [
            {
                "assumption": "The strategic whitespace will remain open long enough to execute",
                "failure_probability": "medium" if whitespace_score < 8.0 else "low",
                "historical_failure_rate": "Category windows typically close in 6-18 months in tech",
                "what_would_expose_it": "Track competitor activity in the same whitespace",
            },
            {
                "assumption": "The supporting evidence is representative, not cherry-picked",
                "failure_probability": "medium",
                "historical_failure_rate": "Confirmation bias affects even rigorous analysts",
                "what_would_expose_it": "Actively seek contradicting sources and count them",
            },
        ]
        
        overall_vulnerability = round(
            min(1.0, len(vulnerability_signals) * 0.12 + (1 - whitespace_score / 10) * 0.3),
            2,
        )
        
        return {
            "thesis_id": thesis_payload.get("id"),
            "anti_thesis": f"The thesis {thesis_payload.get('name', 'unknown')} faces {len(vulnerability_signals)} structural weaknesses that its proponents have not adequately addressed.",
            "anti_thesis_confidence": round(min(0.9, overall_vulnerability + 0.1), 2),
            "load_bearing_assumptions": assumptions,
            "counter_evidence_search": [
                "Search for failed attempts at similar strategic positions",
                "Look for market data contradicting the whitespace claim",
                "Find sources arguing the opposite direction",
            ],
            "failure_modes": [
                {
                    "mode": "Execution failure despite correct thesis",
                    "description": "The strategic insight is right but the team cannot execute",
                    "early_warning_signals": ["Missing milestones", "Resource depletion"],
                    "probability": "medium",
                    "impact": "high",
                },
                {
                    "mode": "Timing mismatch",
                    "description": "The thesis is right but the market timing is wrong",
                    "early_warning_signals": ["Slower than expected adoption", "Competitor inactivity"],
                    "probability": "medium",
                    "impact": "high",
                },
            ],
            "steel_man_opposition": "The strongest argument against is that the evidence base may be narrower than it appears, and the whitespace may close faster than execution can capture it.",
            "market_concerns": ["No direct market validation yet"],
            "timing_risks": ["Market may not be ready"],
            "execution_traps": ["Scope creep from broad strategic ambition"],
            "overall_vulnerability_score": overall_vulnerability,
            "vulnerability_signals": vulnerability_signals,
            "source": "deterministic",
        }
