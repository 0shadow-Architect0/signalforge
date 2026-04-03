"""Time Series Store for Signal Snapshots.

Every analysis pass creates a snapshot. Over time, these snapshots
form a trajectory that reveals the true dynamics of each signal.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class SignalSnapshot(BaseModel):
    """A single point-in-time measurement of a signal/thesis.
    
    Captures the full multi-dimensional state at a specific moment.
    """
    thesis_id: str
    timestamp: str  # ISO 8601
    
    # Core scores (from opportunity evaluation)
    strength: float = Field(default=0.0, ge=0.0, le=10.0)
    novelty: float = Field(default=0.0, ge=0.0, le=10.0)
    urgency: float = Field(default=0.0, ge=0.0, le=10.0)
    founder_fit: float = Field(default=0.0, ge=0.0, le=10.0)
    buildability: float = Field(default=0.0, ge=0.0, le=10.0)
    
    # Derived metrics
    whitespace_score: float = Field(default=0.0, ge=0.0, le=10.0)
    overlap_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    contradiction_severity: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_density: float = Field(default=0.0, ge=0.0, le=1.0)
    freshness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Portfolio context
    portfolio_allocation: float = Field(default=0.0, ge=0.0, le=1.0)
    attention_share: float = Field(default=0.0, ge=0.0, le=1.0)
    
    def score_vector(self) -> list[float]:
        """Return the full score vector for trajectory computation."""
        return [
            self.strength,
            self.novelty,
            self.urgency,
            self.founder_fit,
            self.buildability,
            self.whitespace_score,
            self.overlap_strength,
            self.evidence_density,
            self.freshness_score,
        ]
    
    def composite_score(self) -> float:
        """Weighted average of all scores."""
        weights = [0.20, 0.15, 0.15, 0.10, 0.10, 0.15, 0.05, 0.05, 0.05]
        scores = self.score_vector()
        return round(sum(w * s / 10.0 for w, s in zip(weights, scores)), 3)
    
    def to_dict(self) -> dict:
        return self.model_dump(mode="json")
    
    @classmethod
    def from_thesis_payload(cls, thesis_payload: dict) -> "SignalSnapshot":
        """Create a snapshot from a thesis artifact payload."""
        opportunity = thesis_payload.get("opportunity", {}).get("scores", {})
        whitespace = thesis_payload.get("whitespace", {})
        comparison = thesis_payload.get("comparison", {})
        contradictions = thesis_payload.get("contradictions", {})
        
        severity_map = {"low": 0.2, "medium": 0.5, "high": 0.8}
        sev = contradictions.get("severity", "low")
        
        return cls(
            thesis_id=thesis_payload.get("id", "unknown"),
            timestamp=datetime.now(timezone.utc).isoformat(),
            strength=float(opportunity.get("strategic_leverage", 0) or 0),
            novelty=float(opportunity.get("novelty", 0) or 0),
            urgency=float(opportunity.get("urgency", 0) or 0),
            founder_fit=float(opportunity.get("founder_fit", 0) or 0),
            buildability=float(opportunity.get("buildability", 0) or 0),
            whitespace_score=float(whitespace.get("whitespace_score", 0) or 0),
            overlap_strength=float(comparison.get("overlap_strength", 0) or 0),
            contradiction_severity=severity_map.get(sev, 0.2),
            evidence_density=float(thesis_payload.get("evidence_density", 0) or 0),
            freshness_score=float(thesis_payload.get("freshness_score", 0) or 0.7),
        )


class TimeSeriesStore:
    """In-memory time series store for signal snapshots.
    
    Stores snapshots per thesis and provides time-windowed access.
    In production, this would be backed by SQLite or a time-series DB.
    """
    
    def __init__(self) -> None:
        self._snapshots: dict[str, list[SignalSnapshot]] = {}
    
    def record(self, snapshot: SignalSnapshot) -> None:
        """Record a new snapshot for a thesis."""
        tid = snapshot.thesis_id
        if tid not in self._snapshots:
            self._snapshots[tid] = []
        self._snapshots[tid].append(snapshot)
        # Keep sorted by timestamp
        self._snapshots[tid].sort(key=lambda s: s.timestamp)
    
    def record_thesis(self, thesis_payload: dict) -> SignalSnapshot:
        """Convenience: create and record a snapshot from a thesis payload."""
        snapshot = SignalSnapshot.from_thesis_payload(thesis_payload)
        self.record(snapshot)
        return snapshot
    
    def get_history(self, thesis_id: str) -> list[SignalSnapshot]:
        """Get all snapshots for a thesis, ordered chronologically."""
        return self._snapshots.get(thesis_id, [])
    
    def get_latest(self, thesis_id: str) -> SignalSnapshot | None:
        """Get the most recent snapshot for a thesis."""
        history = self.get_history(thesis_id)
        return history[-1] if history else None
    
    def get_all_thesis_ids(self) -> list[str]:
        """Get all tracked thesis IDs."""
        return sorted(self._snapshots.keys())
    
    def snapshot_count(self, thesis_id: str) -> int:
        return len(self._snapshots.get(thesis_id, []))
    
    def clear(self, thesis_id: str | None = None) -> None:
        """Clear history for a specific thesis or all."""
        if thesis_id:
            self._snapshots.pop(thesis_id, None)
        else:
            self._snapshots.clear()
