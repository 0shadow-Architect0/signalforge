"""Adversarial Engine - Orchestrates the full red team workflow.

Coordinates kill criteria monitoring, red team building, and bias tracking
into a unified adversarial analysis pipeline.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from signalforge.adversarial.kill_criteria import (
    KillCriteriaGenerator,
    KillCriteriaMonitor,
)
from signalforge.adversarial.red_team import RedTeamBuilder
from signalforge.adversarial.bias_tracker import BiasTracker
from signalforge.adversarial.config import AdversarialConfig


class AdversarialEngine:
    """Full adversarial analysis engine.
    
    Usage:
        engine = AdversarialEngine()
        result = engine.audit_thesis(thesis_payload)
        print(result["status"])  # green/yellow/orange/red
    """
    
    def __init__(
        self,
        provider: Any = None,
        config: dict | None = None,
    ) -> None:
        self.provider = provider
        self.config = config or {}
        self.kill_generator = KillCriteriaGenerator()
        self.kill_monitor = KillCriteriaMonitor()
        self.red_team = RedTeamBuilder(provider) if provider else None
        self.bias_tracker = BiasTracker()
    
    def audit_thesis(self, thesis_payload: dict) -> dict:
        """Run a full adversarial audit on a single thesis.
        
        Returns a comprehensive report with:
        - Kill criteria check
        - Red team analysis (if provider available)
        - Bias indicators
        - Overall status and recommendation
        """
        thesis_id = thesis_payload.get("id", "unknown")
        
        # 1. Generate and check kill criteria
        criteria = self.kill_generator.from_thesis(thesis_payload)
        
        state = {
            "id": thesis_id,
            "contradiction_severity": thesis_payload.get("contradictions", {}).get("severity", "low"),
            "freshness_score": 0.7,
            "whitespace_score": float(thesis_payload.get("whitespace", {}).get("whitespace_score", 0) or 0),
            "overlap_strength": float(thesis_payload.get("comparison", {}).get("overlap_strength", 0) or 0),
            "convergence_score": 0.5,
        }
        
        kill_check = self.kill_monitor.check_thesis(criteria, state)
        
        # 2. Run red team analysis
        red_team_result = None
        if self.red_team:
            red_team_result = self.red_team.build_red_team(thesis_payload)
        
        # 3. Check for bias indicators
        bias_indicators = []
        
        asymmetry = self.bias_tracker.detect_evidence_asymmetry(thesis_payload)
        if asymmetry.get("severity", "none") not in ("none", "low"):
            bias_indicators.append(f"evidence_asymmetry:{asymmetry['severity']}")
        
        anchoring = self.bias_tracker.detect_anchoring(thesis_payload)
        if anchoring.get("is_anchored", False):
            bias_indicators.append("anchoring:%s" % anchoring.get("anchoring_risk", "N/A"))
        
        reasoning = self.bias_tracker.detect_motivated_reasoning(thesis_payload)
        bias_indicators.append("motivated_reasoning:%s" % reasoning.get("motivated_reasoning_risk", "N/A"))
        alert_level = kill_check.get("alert_level", "green")
        vulnerability = red_team_result.get("overall_vulnerability_score", 0.5) if red_team_result else 0.5
        
        if alert_level == "red" or vulnerability > 0.7:
            status = "red"
        elif alert_level == "yellow" or vulnerability > 0.5 or len(bias_indicators) > 1:
            status = "orange"
        elif alert_level == "green" and vulnerability < 0.3 and len(bias_indicators) == 0:
            status = "green"
        else:
            status = "yellow"
        
        # 5. Generate recommendation
        recommendation = self._generate_recommendation(status, kill_check, red_team_result, bias_indicators)
        
        return {
            "thesis_id": thesis_id,
            "status": status,
            "alert_level": alert_level,
            "vulnerability_score": vulnerability,
            "kill_criteria_total": len(criteria),
            "kill_criteria_triggered": kill_check.get("triggered_count", 0),
            "kill_criteria_near_miss": kill_check.get("near_miss_count", 0),
            "bias_indicators": bias_indicators,
            "red_team_available": red_team_result is not None,
            "anti_thesis": red_team_result.get("anti_thesis") if red_team_result else None,
            "recommendation": recommendation,
            "audited_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def portfolio_stress_test(self, theses: list[dict]) -> dict:
        """Run adversarial stress test across entire portfolio.
        
        Detects:
        - Portfolio-wide assumption concentration
        - Simultaneous collapse risk
        - Groupthink patterns
        """
        # Generate kill criteria for each thesis
        criteria_by_thesis = {}
        for thesis in theses:
            tid = thesis.get("id")
            criteria_by_thesis[tid] = self.kill_generator.from_thesis(thesis)
        
        # Run portfolio-level kill criteria check
        stress_result = self.kill_monitor.stress_test_portfolio(
            theses, criteria_by_thesis
        )
        
        # Run bias audit
        bias_audit = self.bias_tracker.portfolio_bias_audit(theses)
        
        # Calculate portfolio vulnerability
        total_risk = stress_result.get("simultaneous_collapse_risk", 0)
        bias_risk = 1.0 if bias_audit.get("overall_health") == "critical" else (
            0.6 if bias_audit.get("overall_health") == "warning" else 0.2
        )
        
        composite_risk = round((total_risk + bias_risk) / 2, 2)
        
        return {
            "portfolio_size": len(theses),
            "composite_risk": composite_risk,
            "collapse_risk": total_risk,
            "bias_health": bias_audit.get("overall_health"),
            "theses_at_risk": stress_result.get("theses_at_risk", 0),
            "groupthink_risks": bias_audit.get("groupthink_risks", []),
            "portfolio_alert_level": stress_result.get("portfolio_alert_level", "green"),
            "recommendation": self._portfolio_recommendation(composite_risk, stress_result, bias_audit),
            "stress_tested_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def _generate_recommendation(
        self,
        status: str,
        kill_check: dict,
        red_team: dict | None,
        biases: list[str],
    ) -> str:
        """Generate actionable recommendation based on audit results."""
        if status == "red":
            parts = ["CRITICAL: Thesis faces significant adversarial pressure."]
            if kill_check.get("triggered_count", 0) > 0:
                parts.append(f"Kill criteria triggered: {kill_check['triggered_count']}. Review immediately.")
            if red_team and red_team.get("overall_vulnerability_score", 0) > 0.7:
                parts.append(f"Vulnerability score: {red_team['overall_vulnerability_score']}. Consider refining or abandoning.")
            return " ".join(parts)
        
        elif status == "orange":
            parts = ["WARNING: Thesis shows concerning signals."]
            if biases:
                parts.append(f"Bias indicators: {', '.join(biases)}. Actively seek disconfirming evidence.")
            if kill_check.get("near_miss_count", 0) > 0:
                parts.append(f"{kill_check['near_miss_count']} kill criteria near-miss. Monitor closely.")
            return " ".join(parts)
        
        elif status == "yellow":
            return "MODERATE: Thesis is holding but has some weakness. Continue monitoring and seek broader evidence."
        
        else:
            return "HEALTHY: Thesis shows good adversarial resilience. Maintain vigilance."
    
    def _portfolio_recommendation(
        self,
        composite_risk: float,
        stress_result: dict,
        bias_audit: dict,
    ) -> str:
        """Generate portfolio-level recommendation."""
        if composite_risk > 0.6:
            return f"HIGH RISK: Portfolio composite risk is {composite_risk}. Diversify assumptions immediately. {stress_result.get('theses_at_risk', 0)} theses at risk of simultaneous collapse."
        elif composite_risk > 0.3:
            return f"MODERATE RISK: Portfolio shows concentration. Consider diversifying across independent assumptions. Groupthink risks: {len(bias_audit.get('groupthink_risks', []))}."
        else:
            return f"LOW RISK: Portfolio is well-diversified. Continue monitoring. Current alert: {stress_result.get('portfolio_alert_level', 'green')}."
