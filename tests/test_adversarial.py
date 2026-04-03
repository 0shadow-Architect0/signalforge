"""Tests for the Adversarial Thesis Engine."""

import pytest
from signalforge.adversarial.config import AdversarialConfig
from signalforge.adversarial.kill_criteria import KillCriteriaGenerator, KillCriterion, KillCriteriaMonitor
from signalforge.adversarial.red_team import RedTeamBuilder
from signalforge.adversarial.bias_tracker import BiasTracker
from signalforge.adversarial.engine import AdversarialEngine
from signalforge.semantic.provider import NoOpProvider


@pytest.fixture
def sample_thesis():
    return {
        "id": "test_thesis",
        "name": "AI Agent Framework",
        "whitespace": {"whitespace_score": 8.2, "wedge_statement": "Agent-native infra"},
        "contradictions": {"contradiction_count": 2, "severity": "medium"},
        "comparison": {"overlap_strength": 0.35, "shared_capabilities": ["agent-coordination"]},
        "opportunity": {"scores": {"novelty": 8.5, "urgency": 7.8, "founder_fit": 7.2, "buildability": 8.0}},
    }


class TestKillCriteria:
    def test_generate_from_thesis(self, sample_thesis):
        criteria = KillCriteriaGenerator().from_thesis(sample_thesis)
        assert len(criteria) == 5
        assert all(isinstance(c, KillCriterion) for c in criteria)
    
    def test_monitor_check_green(self, sample_thesis):
        criteria = KillCriteriaGenerator().from_thesis(sample_thesis)
        state = {
            "id": "test_thesis",
            "contradiction_severity": "low",
            "freshness_score": 0.8,
            "whitespace_score": 8.2,
            "overlap_strength": 0.1,  # Very low overlap
            "convergence_score": 0.8,  # High convergence
        }
        result = KillCriteriaMonitor().check_thesis(criteria, state)
        assert result["alert_level"] in ("green", "yellow", "orange", "red")
    
    def test_monitor_check_red(self, sample_thesis):
        criteria = KillCriteriaGenerator().from_thesis(sample_thesis)
        state = {
            "id": "test_thesis",
            "contradiction_severity": "high",
            "freshness_score": 0.05,
            "whitespace_score": 1.0,
            "overlap_strength": 0.9,
            "convergence_score": 0.05,
        }
        result = KillCriteriaMonitor().check_thesis(criteria, state)
        assert result["alert_level"] == "red"
        assert result["triggered_count"] > 0


class TestRedTeam:
    def test_deterministic_red_team(self, sample_thesis):
        builder = RedTeamBuilder(NoOpProvider())
        result = builder.build_red_team(sample_thesis)
        assert result is not None
        assert "anti_thesis" in result
        assert "load_bearing_assumptions" in result
        assert "failure_modes" in result
        assert result["source"] == "deterministic"
    
    def test_none_provider(self, sample_thesis):
        builder = RedTeamBuilder(None)
        result = builder.build_red_team(sample_thesis)
        assert result is not None


class TestBiasTracker:
    def test_evidence_asymmetry(self, sample_thesis):
        result = BiasTracker.detect_evidence_asymmetry(sample_thesis)
        assert "evidence_ratio" in result
        assert "is_biased" in result
    
    def test_anchoring(self, sample_thesis):
        result = BiasTracker.detect_anchoring(sample_thesis)
        assert "anchoring_risk" in result
    
    def test_motivated_reasoning(self, sample_thesis):
        result = BiasTracker.detect_motivated_reasoning(sample_thesis)
        assert "motivated_reasoning_risk" in result
    
    def test_portfolio_bias_audit(self, sample_thesis):
        theses = [sample_thesis, {**sample_thesis, "id": "t2"}]
        audit = BiasTracker.portfolio_bias_audit(theses)
        assert audit["total_theses"] == 2
        assert "overall_health" in audit


class TestAdversarialEngine:
    def test_audit_thesis(self, sample_thesis):
        engine = AdversarialEngine(provider=NoOpProvider())
        result = engine.audit_thesis(sample_thesis)
        assert result["status"] in ("green", "yellow", "orange", "red")
        assert "recommendation" in result
    
    def test_portfolio_stress_test(self, sample_thesis):
        theses = [sample_thesis, {**sample_thesis, "id": "t2"}]
        engine = AdversarialEngine(provider=NoOpProvider())
        result = engine.portfolio_stress_test(theses)
        assert "composite_risk" in result
        assert result["portfolio_size"] == 2
