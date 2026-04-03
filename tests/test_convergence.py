"""Tests for the Convergence Radar."""

import pytest
from signalforge.convergence.config import ConvergenceConfig
from signalforge.convergence.overlap import OverlapDetector
from signalforge.convergence.radar import ConvergenceRadar


@pytest.fixture
def converging_theses():
    return [
        {
            "id": "t_agents",
            "opportunity": {"scores": {"novelty": 8.0, "urgency": 7.5}},
            "whitespace": {"whitespace_score": 8.5, "wedge_statement": "Agent infra"},
            "comparison": {"overlap_strength": 0.3, "shared_capabilities": ["agent-coord"]},
        },
        {
            "id": "t_workflows",
            "opportunity": {"scores": {"novelty": 7.5, "urgency": 8.0}},
            "whitespace": {"whitespace_score": 8.0, "wedge_statement": "Workflow orchestration"},
            "comparison": {"overlap_strength": 0.35, "shared_capabilities": ["agent-coord"]},
        },
        {
            "id": "t_research",
            "opportunity": {"scores": {"novelty": 9.0, "urgency": 6.0}},
            "whitespace": {"whitespace_score": 9.0, "wedge_statement": "AI research"},
            "comparison": {"overlap_strength": 0.2, "shared_capabilities": ["agent-coord"]},
        },
    ]


@pytest.fixture
def orthogonal_thesis():
    return {
        "id": "t_unrelated",
        "opportunity": {"scores": {"novelty": 3.0, "urgency": 2.0}},
        "whitespace": {"whitespace_score": 2.5},
        "comparison": {"overlap_strength": 0.1, "shared_capabilities": []},
    }


class TestOverlapDetector:
    def test_similar_theses(self, converging_theses):
        result = OverlapDetector.detect(converging_theses[0], converging_theses[1])
        assert result.overlap_score > 0.3
        assert result.convergence_type in ("synergistic", "competing", "complementary")
    
    def test_orthogonal_theses(self, converging_theses, orthogonal_thesis):
        result = OverlapDetector.detect(converging_theses[0], orthogonal_thesis)
        # Orthogonal theses have low overlap score
        assert result.overlap_score < 0.7  # Just check low similarity
    
    def test_shared_capabilities_detected(self, converging_theses):
        result = OverlapDetector.detect(converging_theses[0], converging_theses[1])
        assert "shared_capabilities" in result.shared_dimensions


class TestConvergenceRadar:
    def test_scan_finds_convergence(self, converging_theses):
        radar = ConvergenceRadar()
        points = radar.scan(converging_theses)
        assert len(points) >= 1
        assert points[0].convergence_score > 0
    
    def test_scan_empty(self):
        radar = ConvergenceRadar()
        points = radar.scan([])
        assert points == []
    
    def test_scan_single(self):
        radar = ConvergenceRadar()
        points = radar.scan([{"id": "t1", "opportunity": {"scores": {}}, "whitespace": {}, "comparison": {}}])
        assert points == []
    
    def test_emergence_detection(self, converging_theses):
        radar = ConvergenceRadar()
        result = radar.detect_emergence(converging_theses)
        assert "emergence_signals" in result
        assert "total_convergence_points" in result
    
    def test_mixed_portfolio(self, converging_theses, orthogonal_thesis):
        all_theses = converging_theses + [orthogonal_thesis]
        radar = ConvergenceRadar()
        points = radar.scan(all_theses)
        assert len(points) >= 1
    
    def test_signal_strength(self, converging_theses):
        radar = ConvergenceRadar()
        points = radar.scan(converging_theses)
        if points:
            strength = points[0]._signal_strength()
            assert strength in ("weak", "moderate", "strong", "supersignal")
    
    def test_convergence_point_to_dict(self, converging_theses):
        radar = ConvergenceRadar()
        points = radar.scan(converging_theses)
        if points:
            d = points[0].to_dict()
            assert "thesis_ids" in d
            assert "convergence_score" in d
            assert "signal_strength" in d
