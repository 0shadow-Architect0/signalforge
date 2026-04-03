"""Bias Tracker - Detects and tracks confirmation bias patterns.

Innovation: Most tools amplify your biases. This one actively measures them.
Tracks your evidence collection patterns, identifies cherry-picking, and 
generates quarterly bias audit reports.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class BiasTracker:
    """Tracks confirmation bias across a portfolio of theses.
    
    Detects:
    - Evidence asymmetry (too much confirming, too little disconfirming)
    - Anchoring (overweighting early evidence)
    - Motivated reasoning (explaining away contradictions)
    - Portfolio groupthink (all theses sharing same assumptions)
    """
    
    @staticmethod
    def detect_evidence_asymmetry(
        thesis_payload: dict,
        threshold: float = 3.0,
    ) -> dict:
        """Check if evidence balance is skewed toward confirmation.
        
        Args:
            thesis_payload: The thesis artifact payload
            threshold: Ratio of confirming:disconfirming that triggers alert
            
        Returns:
            Evidence asymmetry analysis
        """
        comparison = thesis_payload.get("comparison", {})
        contradictions = thesis_payload.get("contradictions", {})
        
        # Count supporting vs contradicting signals
        shared_caps = len(comparison.get("shared_capabilities", []))
        diff_zones = len(comparison.get("differentiation_zones", []))
        contradiction_count = contradictions.get("contradiction_count", 0)
        contradiction_severity = contradictions.get("severity", "low")
        
        confirming = max(1, shared_caps)
        disconfirming = max(1, contradiction_count + diff_zones)
        
        ratio = confirming / disconfirming
        
        # Analyze severity
        is_biased = ratio > threshold
        severity = "none"
        if ratio > 5.0:
            severity = "critical"
        elif ratio > threshold:
            severity = "high"
        elif ratio > threshold * 0.7:
            severity = "moderate"
        
        return {
            "thesis_id": thesis_payload.get("id"),
            "confirming_signals": confirming,
            "disconfirming_signals": disconfirming,
            "evidence_ratio": round(ratio, 2),
            "threshold": threshold,
            "is_biased": is_biased,
            "bias_severity": severity,
            "recommendation": (
                "Seek at least {} more disconfirming sources"
                .format(max(0, int(confirming / threshold) - disconfirming))
                if is_biased else "Evidence balance is healthy"
            ),
        }
    
    @staticmethod
    def detect_anchoring(thesis_payload: dict) -> dict:
        """Check if thesis is overly anchored on early evidence.
        
        Anchoring detection: if the first sources have disproportionate 
        weight in the analysis, the thesis may be anchored.
        """
        freshness = thesis_payload.get("freshness", {})
        comparison = thesis_payload.get("comparison", {})
        
        freshness_score = freshness.get("average_score", 0.7)
        source_count = comparison.get("source_count", 0)
        
        # Low freshness + high confidence = anchoring risk
        anchoring_risk = 0.0
        if freshness_score < 0.4 and source_count > 3:
            anchoring_risk = 0.7
        elif freshness_score < 0.5 and source_count > 5:
            anchoring_risk = 0.5
        elif freshness_score < 0.6:
            anchoring_risk = 0.3
        
        return {
            "thesis_id": thesis_payload.get("id"),
            "freshness_score": freshness_score,
            "source_count": source_count,
            "anchoring_risk": round(anchoring_risk, 2),
            "is_anchored": anchoring_risk > 0.5,
            "recommendation": (
                "Refresh evidence base - sources may be stale"
                if anchoring_risk > 0.5 else "Anchoring risk is low"
            ),
        }
    
    @staticmethod
    def detect_motivated_reasoning(thesis_payload: dict) -> dict:
        """Check if contradictions are being explained away.
        
        Motivated reasoning: when contradiction severity is high but
        the thesis still has high confidence scores.
        """
        contradictions = thesis_payload.get("contradictions", {})
        opportunity = thesis_payload.get("opportunity", {}).get("scores", {})
        whitespace = thesis_payload.get("whitespace", {})
        
        contradiction_severity = contradictions.get("severity", "low")
        contradiction_count = contradictions.get("contradiction_count", 0)
        
        # Get average opportunity score
        scores = [v for v in opportunity.values() if isinstance(v, (int, float))]
        avg_score = sum(scores) / max(1, len(scores)) if scores else 7.0
        
        # High confidence + high contradictions = motivated reasoning
        reasoning_risk = 0.0
        if contradiction_severity == "high" and avg_score > 7.5:
            reasoning_risk = 0.8
        elif contradiction_severity == "medium" and avg_score > 8.0:
            reasoning_risk = 0.6
        elif contradiction_count > 3 and avg_score > 7.5:
            reasoning_risk = 0.4
        
        return {
            "thesis_id": thesis_payload.get("id"),
            "contradiction_severity": contradiction_severity,
            "contradiction_count": contradiction_count,
            "average_confidence": round(avg_score, 2),
            "motivated_reasoning_risk": round(reasoning_risk, 2),
            "is_motivated": reasoning_risk > 0.5,
            "recommendation": (
                "Re-examine contradictions - confidence may be inflated"
                if reasoning_risk > 0.5 else "No motivated reasoning detected"
            ),
        }
    
    @staticmethod
    def portfolio_bias_audit(theses: list[dict]) -> dict:
        """Run a full bias audit across all theses.
        
        Innovation: Portfolio-level bias detection - finds patterns 
        across all theses, not just within each one.
        """
        if not theses:
            return {"status": "no_theses", "bias_indicators": []}
        
        biases_found = []
        
        for thesis in theses:
            asymmetry = BiasTracker.detect_evidence_asymmetry(thesis)
            anchoring = BiasTracker.detect_anchoring(thesis)
            reasoning = BiasTracker.detect_motivated_reasoning(thesis)
            
            if asymmetry["is_biased"]:
                biases_found.append({
                    "thesis_id": thesis.get("id"),
                    "bias_type": "evidence_asymmetry",
                    "severity": asymmetry["bias_severity"],
                    "detail": asymmetry["recommendation"],
                })
            
            if anchoring["is_anchored"]:
                biases_found.append({
                    "thesis_id": thesis.get("id"),
                    "bias_type": "anchoring",
                    "severity": "high" if anchoring["anchoring_risk"] > 0.6 else "moderate",
                    "detail": anchoring["recommendation"],
                })
            
            if reasoning["is_motivated"]:
                biases_found.append({
                    "thesis_id": thesis.get("id"),
                    "bias_type": "motivated_reasoning",
                    "severity": "high" if reasoning["motivated_reasoning_risk"] > 0.6 else "moderate",
                    "detail": reasoning["recommendation"],
                })
        
        # Portfolio-level groupthink detection
        all_assumptions = []
        for thesis in theses:
            assumptions = thesis.get("assumptions", [])
            all_assumptions.extend(assumptions)
        
        shared_assumptions = {}
        for a in all_assumptions:
            key = str(a).lower()[:50]
            shared_assumptions[key] = shared_assumptions.get(key, 0) + 1
        
        groupthink_risks = [
            {"assumption": k, "thesis_count": v}
            for k, v in shared_assumptions.items() if v > 1
        ]
        
        total_theses = len(theses)
        theses_with_bias = len(set(b["thesis_id"] for b in biases_found))
        
        return {
            "audit_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_theses": total_theses,
            "theses_with_bias": theses_with_bias,
            "bias_rate": round(theses_with_bias / max(1, total_theses), 2),
            "biases_found": biases_found,
            "groupthink_risks": groupthink_risks,
            "overall_health": (
                "critical" if theses_with_bias > total_theses * 0.5 else
                "warning" if theses_with_bias > total_theses * 0.3 else
                "healthy"
            ),
        }
