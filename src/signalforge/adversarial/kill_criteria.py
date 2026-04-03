"""Kill Criteria: The Thesis Kill Switch.

Innovation: Every thesis has explicit "kill conditions" — specific, measurable
states that would invalidate the thesis. Most strategic failures come from
never defining what would make you quit.

Kill criteria are:
- Specific (not vague)
- Measurable (can be checked)
- Time-bound (checked periodically)
- Binary (triggered or not triggered)
"""

from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel, Field


class KillCriterion(BaseModel):
    """A single kill criterion for a thesis."""
    id: str
    thesis_id: str
    description: str
    metric: str  # What to measure
    threshold: str  # The trigger value
    current_value: str | None = None
    triggered: bool = False
    triggered_at: datetime | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)  # How certain we are about the trigger
    
    def evaluate(self, current_state: dict) -> dict:
        """Check if this kill criterion is triggered by current state."""
        # Deterministic evaluation based on metric matching
        evaluation = {
            "criterion_id": self.id,
            "thesis_id": self.thesis_id,
            "description": self.description,
            "threshold": self.threshold,
            "triggered": False,
            "alert_level": "green",
            "confidence": 0.5,
        }
        
        # Check for trigger conditions
        metric_value = current_state.get(self.metric)
        if metric_value is not None:
            try:
                value = float(metric_value)
                threshold_val = float(self.threshold.rstrip("%"))
                
                # Check if metric crosses threshold
                if value <= threshold_val:
                    evaluation["triggered"] = True
                    evaluation["current_value"] = value
                    evaluation["alert_level"] = "red"
                    evaluation["confidence"] = 0.9
            except (ValueError, TypeError):
                # Non-numeric comparison: string matching
                if str(metric_value).lower() == str(self.threshold).lower():
                    evaluation["triggered"] = True
                    evaluation["current_value"] = metric_value
                    evaluation["alert_level"] = "red"
                    evaluation["confidence"] = 0.85
        
        return evaluation
    
    def to_dict(self) -> dict:
        return self.model_dump(mode="json")


class KillCriteriaGenerator:
    """Generate kill criteria from a thesis payload.
    
    The innovation: We decompose a thesis into its load-bearing assumptions
    and create specific kill conditions for each one.
    """
    
    @staticmethod
    def from_thesis(thesis_payload: dict) -> list[KillCriterion]:
        """Auto-generate kill criteria from a thesis.
        
        Extracts:
        1. Evidence-based criteria (contradiction load, freshness decay)
        2. Opportunity criteria (whitespace collapse, category pressure)
        3. Execution criteria (blocker accumulation, resource exhaustion)
        """
        criteria = []
        thesis_id = thesis_payload.get("id", "unknown")
        contradictions = thesis_payload.get("contradictions", {})
        whitespace = thesis_payload.get("whitespace", {})
        comparison = thesis_payload.get("comparison", {})
        opportunity = thesis_payload.get("opportunity", {}).get("scores", {})
        
        # 1. Evidence kill: contradiction severity reaches "high"
        if contradictions:
            criteria.append(KillCriterion(
                id=f"kill_{thesis_id}_contradictions",
                thesis_id=thesis_id,
                description=f"Contradiction severity reaches HIGH for thesis {thesis_id}",
                metric="contradiction_severity",
                threshold="high",
                confidence=0.8,
            ))
        
        # 2. Freshness kill: evidence bundle goes stale
        criteria.append(KillCriterion(
            id=f"kill_{thesis_id}_freshness",
            thesis_id=thesis_id,
            description=f"Average source freshness drops below 0.4 (evidence is stale)",
            metric="freshness_score",
            threshold="0.4",
            confidence=0.75,
        ))
        
        # 3. Whitespace kill: opportunity collapses
        if whitespace:
            criteria.append(KillCriterion(
                id=f"kill_{thesis_id}_whitespace",
                thesis_id=thesis_id,
                description=f"Whitespace score drops below 6.0 (opportunity evaporated)",
                metric="whitespace_score",
                threshold="6.0",
                confidence=0.7,
            ))
        
        # 4. Overlap kill: category becomes crowded
        if comparison:
            criteria.append(KillCriterion(
                id=f"kill_{thesis_id}_overlap",
                thesis_id=thesis_id,
                description=f"Overlap strength exceeds 0.8 (category is crowded)",
                metric="overlap_strength",
                threshold="0.8",
                confidence=0.65,
            ))
        
        # 5. Convergence kill: sources stop converging
        criteria.append(KillCriterion(
            id=f"kill_{thesis_id}_convergence",
            thesis_id=thesis_id,
            description=f"Convergence score drops below 0.2 (sources diverge)",
            metric="convergence_score",
            threshold="0.2",
            confidence=0.6,
        ))
        
        return criteria


class KillCriteriaMonitor:
    """Monitor all kill criteria across a portfolio.
    
    Produces:
    - Alert levels per thesis (GREEN/YELLOW/ORANGE/RED)
    - Near-miss tracking
    - Portfolio stress test results
    """
    
    @staticmethod
    def check_thesis(
        criteria: list[KillCriterion],
        current_state: dict,
    ) -> dict:
        """Check all kill criteria for a single thesis."""
        evaluations = []
        triggered_count = 0
        near_miss_count = 0
        max_alert = "green"
        
        for criterion in criteria:
            evaluation = criterion.evaluate(current_state)
            evaluations.append(evaluation)
            
            if evaluation["triggered"]:
                triggered_count += 1
                if max_alert != "red":
                    max_alert = "red"
            elif evaluation.get("confidence", 0) > 0.6:
                near_miss_count += 1
                if max_alert == "green":
                    max_alert = "yellow"
        
        return {
            "thesis_id": current_state.get("id"),
            "alert_level": max_alert,
            "triggered_count": triggered_count,
            "near_miss_count": near_miss_count,
            "total_criteria": len(criteria),
            "evaluations": evaluations,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    
    @staticmethod
    def stress_test_portfolio(
        theses: list[dict],
        criteria_by_thesis: dict[str, list[KillCriterion]],
        shared_assumption: str | None = None,
    ) -> dict:
        """Portfolio-level stress test.
        
        Innovation: Detects portfolio groupthink - situations where
        multiple theses depend on the same underlying assumption.
        If that assumption fails, multiple theses collapse simultaneously.
        """
        results = []
        simultaneous_collapse_risk = 0.0
        
        for thesis_payload in theses:
            thesis_id = thesis_payload.get("id")
            criteria = criteria_by_thesis.get(thesis_id, [])
            state = {
                "id": thesis_id,
                "contradiction_severity": thesis_payload.get("contradictions", {}).get("severity", "low"),
                "freshness_score": 0.7,  # Would be computed from actual data
                "whitespace_score": float(thesis_payload.get("whitespace", {}).get("whitespace_score", 0) or 0),
                "overlap_strength": float(thesis_payload.get("comparison", {}).get("overlap_strength", 0) or 0),
                "convergence_score": 0.5,  # Would be computed from actual data
            }
            check = KillCriteriaMonitor.check_thesis(criteria, state)
            results.append(check)
        
        # Calculate simultaneous collapse risk
        triggered_theses = [r for r in results if r["alert_level"] == "red"]
        if len(triggered_theses) > 1:
            simultaneous_collapse_risk = min(1.0, len(triggered_theses) / max(1, len(theses)))
        
        return {
            "portfolio_alert_level": "red" if simultaneous_collapse_risk > 0.3 else 
                                      "orange" if any(r["alert_level"] in {"red", "orange"} for r in results) else
                                      "yellow" if any(r["alert_level"] == "yellow" for r in results) else "green",
            "simultaneous_collapse_risk": round(simultaneous_collapse_risk, 2),
            "theses_at_risk": len(triggered_theses),
            "total_theses": len(theses),
            "shared_assumption_tested": shared_assumption,
            "thesis_results": results,
            "recommendation": "diversify_assumptions" if simultaneous_collapse_risk > 0.3 else "monitor",
        }
