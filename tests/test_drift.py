"""Tests for the SignalDrift Engine."""

import pytest
from signalforge.drift.config import DriftConfig
from signalforge.drift.timeseries import SignalSnapshot, TimeSeriesStore
from signalforge.drift.analyzer import DriftAnalyzer
from signalforge.drift.classifier import SignalClassifier, SignalPhase


@pytest.fixture
def store_with_history():
    store = TimeSeriesStore()
    for i in range(5):
        store.record_thesis({
            "id": "thesis_test",
            "opportunity": {"scores": {
                "novelty": 5.0 + i * 0.8,
                "urgency": 4.0 + i * 0.6,
                "founder_fit": 6.0 + i * 0.5,
                "buildability": 5.0 + i * 0.4,
            }},
            "whitespace": {"whitespace_score": 5.0 + i * 0.7},
            "comparison": {"overlap_strength": 0.3},
            "contradictions": {"contradiction_count": 1, "severity": "low"},
        })
    return store


class TestTimeSeriesStore:
    def test_record_and_retrieve(self):
        store = TimeSeriesStore()
        store.record_thesis({"id": "t1", "opportunity": {"scores": {"novelty": 5.0}}})
        assert store.snapshot_count("t1") == 1
    
    def test_get_latest(self):
        store = TimeSeriesStore()
        store.record_thesis({"id": "t1", "opportunity": {"scores": {"novelty": 5.0}}})
        latest = store.get_latest("t1")
        assert latest is not None
        assert latest.thesis_id == "t1"
    
    def test_clear(self):
        store = TimeSeriesStore()
        store.record_thesis({"id": "t1", "opportunity": {"scores": {"novelty": 5.0}}})
        store.clear("t1")
        assert store.snapshot_count("t1") == 0


class TestSignalSnapshot:
    def test_from_thesis_payload(self):
        thesis = {
            "id": "t1",
            "opportunity": {"scores": {"novelty": 8.0, "urgency": 7.0}},
            "whitespace": {"whitespace_score": 7.5},
            "comparison": {"overlap_strength": 0.4},
            "contradictions": {"severity": "medium", "contradiction_count": 2},
        }
        snapshot = SignalSnapshot.from_thesis_payload(thesis)
        assert snapshot.thesis_id == "t1"
        assert snapshot.novelty == 8.0
        assert snapshot.contradiction_severity == 0.5  # medium
    
    def test_composite_score(self):
        snapshot = SignalSnapshot(thesis_id="t1", timestamp="2025-01-01T00:00:00Z", strength=8.0)
        assert 0.0 <= snapshot.composite_score() <= 1.0


class TestDriftAnalyzer:
    def test_analyze_strengthening(self, store_with_history):
        analyzer = DriftAnalyzer(store_with_history)
        vector = analyzer.analyze("thesis_test")
        assert vector.classification == "strengthening"
        assert vector.snapshot_count == 5
        assert len(vector.velocity) > 0
    
    def test_analyze_insufficient_data(self):
        store = TimeSeriesStore()
        store.record_thesis({"id": "t1", "opportunity": {"scores": {"novelty": 5.0}}})
        analyzer = DriftAnalyzer(store)
        vector = analyzer.analyze("t1")
        assert vector.classification == "insufficient_data"
    
    def test_portfolio_analysis(self, store_with_history):
        analyzer = DriftAnalyzer(store_with_history)
        result = analyzer.analyze_portfolio()
        assert result["total_theses"] == 1
    
    def test_divergence_detection(self, store_with_history):
        # Add a declining thesis
        for i in range(3):
            store_with_history.record_thesis({
                "id": "thesis_declining",
                "opportunity": {"scores": {"novelty": 8.0 - i * 2.0, "urgency": 7.0 - i * 1.5}},
                "whitespace": {"whitespace_score": 7.0 - i * 1.0},
                "comparison": {"overlap_strength": 0.5},
                "contradictions": {"severity": "high", "contradiction_count": 3},
            })
        
        analyzer = DriftAnalyzer(store_with_history)
        divs = analyzer.detect_divergence(["thesis_test", "thesis_declining"])
        assert len(divs) >= 1
        assert "divergence_strength" in divs[0]


class TestSignalClassifier:
    def test_classify_strengthening(self):
        drift_dict = {
            "thesis_id": "t1",
            "classification": "strengthening",
            "momentum": 0.5,
            "volatility": 0.1,
            "velocity": {"novelty": 0.01},
            "snapshot_count": 5,
            "confidence": 0.5,
        }
        result = SignalClassifier.classify(drift_dict)
        assert result.phase == SignalPhase.STRENGTHENING
        assert result.thesis_id == "t1"
    
    def test_classify_emerging(self):
        drift_dict = {
            "thesis_id": "t2",
            "classification": "emerging",
            "momentum": 0.1,
            "volatility": 0.05,
            "velocity": {},
            "snapshot_count": 3,
            "confidence": 0.3,
        }
        result = SignalClassifier.classify(drift_dict)
        assert result.phase == SignalPhase.EMERGING
    
    def test_classify_decaying(self):
        drift_dict = {
            "thesis_id": "t3",
            "classification": "decaying",
            "momentum": -0.3,
            "volatility": 0.2,
            "velocity": {},
            "snapshot_count": 8,
            "confidence": 0.8,
        }
        result = SignalClassifier.classify(drift_dict)
        assert result.phase == SignalPhase.DECAYING
