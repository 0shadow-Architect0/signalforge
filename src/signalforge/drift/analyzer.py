"""Drift Analyzer - Computes velocity, acceleration, and momentum.

The core innovation: treating every thesis/signal as a particle in 
multi-dimensional score space, and computing its kinematics.

Just like quantitative finance tracks price velocity and momentum for assets,
we track score velocity and momentum for strategic signals.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from signalforge.drift.timeseries import SignalSnapshot, TimeSeriesStore
from signalforge.drift.config import DriftConfig


def _parse_ts(timestamp: str) -> datetime:
    """Parse ISO timestamp."""
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc)


def _days_between(a: str, b: str) -> float:
    """Days between two ISO timestamps."""
    dt_a = _parse_ts(a)
    dt_b = _parse_ts(b)
    delta = abs((dt_b - dt_a).total_seconds())
    return max(0.01, delta / 86400)  # At least 0.01 days to avoid division by zero


class DriftVector:
    """A multi-dimensional velocity/acceleration vector for a signal."""
    
    def __init__(self, thesis_id: str) -> None:
        self.thesis_id = thesis_id
        self.velocity: dict[str, float] = {}
        self.acceleration: dict[str, float] = {}
        self.momentum: float = 0.0
        self.volatility: float = 0.0
        self.classification: str = "unknown"
        self.confidence: float = 0.0
        self.period_days: float = 0.0
        self.snapshot_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            "thesis_id": self.thesis_id,
            "velocity": self.velocity,
            "acceleration": self.acceleration,
            "momentum": round(self.momentum, 4),
            "volatility": round(self.volatility, 4),
            "classification": self.classification,
            "confidence": round(self.confidence, 3),
            "period_days": round(self.period_days, 1),
            "snapshot_count": self.snapshot_count,
        }


class DriftAnalyzer:
    """Analyzes temporal dynamics of signals.
    
    For each thesis, computes:
    - Velocity: rate of change per score dimension (per day)
    - Acceleration: is change speeding up or slowing down
    - Momentum: strength * velocity (signals that are both strong AND moving)
    - Volatility: how noisy/unstable is the signal
    
    Classification:
    - EMERGING: low current strength, high positive velocity (getting stronger fast)
    - STRENGTHENING: growing strength and confidence
    - STABLE: steady state
    - DECAYING: negative velocity on key dimensions
    - VOLATILE: high volatility, unpredictable
    - DORMANT: no significant change
    """
    
    def __init__(self, store: TimeSeriesStore, config: DriftConfig | None = None) -> None:
        self.store = store
        self.config = config or DriftConfig()
    
    def analyze(self, thesis_id: str) -> DriftVector:
        """Compute full drift analysis for a single thesis."""
        history = self.store.get_history(thesis_id)
        vector = DriftVector(thesis_id)
        vector.snapshot_count = len(history)
        
        if len(history) < 2:
            vector.classification = "insufficient_data"
            vector.confidence = 0.0
            return vector
        
        latest = history[-1]
        first = history[0]
        vector.period_days = _days_between(first.timestamp, latest.timestamp)
        
        # Compute velocity (change per day for each dimension)
        dimensions = [
            "strength", "novelty", "urgency", "founder_fit", "buildability",
            "whitespace_score", "overlap_strength", "evidence_density", "freshness_score",
        ]
        
        for dim in dimensions:
            latest_val = getattr(latest, dim, 0)
            first_val = getattr(first, dim, 0)
            delta = latest_val - first_val
            velocity = delta / vector.period_days
            vector.velocity[dim] = round(velocity, 4)
        
        # Compute acceleration (if 3+ snapshots, compare recent vs early velocity)
        if len(history) >= 3:
            mid = len(history) // 2
            for dim in dimensions:
                recent_vel = (getattr(history[-1], dim, 0) - getattr(history[mid], dim, 0)) / max(0.01, _days_between(history[mid].timestamp, history[-1].timestamp))
                early_vel = (getattr(history[mid], dim, 0) - getattr(history[0], dim, 0)) / max(0.01, _days_between(history[0].timestamp, history[mid].timestamp))
                vector.acceleration[dim] = round(recent_vel - early_vel, 4)
        
        # Compute momentum: composite_score * average_velocity_magnitude
        composite = latest.composite_score()
        avg_velocity = sum(abs(v) for v in vector.velocity.values()) / max(1, len(vector.velocity))
        direction = 1.0 if sum(vector.velocity.values()) > 0 else -1.0
        vector.momentum = composite * avg_velocity * direction
        
        # Compute volatility: standard deviation of score changes
        if len(history) >= 3:
            composites = [s.composite_score() for s in history]
            mean_c = sum(composites) / len(composites)
            variance = sum((c - mean_c) ** 2 for c in composites) / len(composites)
            vector.volatility = round(variance ** 0.5, 4)
        
        # Classify the signal
        vector.classification = self._classify(vector, latest)
        vector.confidence = round(min(1.0, len(history) / 10), 3)
        
        return vector
    
    def analyze_portfolio(self) -> dict:
        """Analyze drift across all tracked theses."""
        results = {}
        for thesis_id in self.store.get_all_thesis_ids():
            results[thesis_id] = self.analyze(thesis_id).to_dict()
        
        # Portfolio-level insights
        classifications = [r["classification"] for r in results.values()]
        
        return {
            "total_theses": len(results),
            "classifications": {
                cls: classifications.count(cls)
                for cls in set(classifications)
            },
            "highest_momentum": max(
                results.items(), key=lambda x: x[1].get("momentum", 0), default=(None, {})
            )[0],
            "most_volatile": max(
                results.items(), key=lambda x: x[1].get("volatility", 0), default=(None, {})
            )[0],
            "theses": results,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def _classify(self, vector: DriftVector, latest: SignalSnapshot) -> str:
        """Classify signal trajectory."""
        composite = latest.composite_score()
        avg_velocity = sum(vector.velocity.values()) / max(1, len(vector.velocity))
        cfg = self.config
        
        # Volatile: high noise regardless of direction
        if vector.volatility > cfg.volatility_threshold:
            return "volatile"
        
        # Dormant: barely moving
        if abs(avg_velocity) < 0.001 and vector.volatility < 0.05:
            return "dormant"
        
        # Emerging: low strength but high positive velocity
        if composite < 0.4 and avg_velocity > cfg.emerging_velocity_threshold / 30:
            return "emerging"
        
        # Decaying: clear negative velocity
        if avg_velocity < cfg.decay_velocity_threshold / 30:
            return "decaying"
        
        # Strengthening: positive velocity + growing
        if avg_velocity > 0.002:
            return "strengthening"
        
        # Stable: everything else
        return "stable"
    
    def detect_divergence(self, thesis_ids: list[str]) -> list[dict]:
        """Detect when two signals are diverging (moving in opposite directions).
        
        Innovation: Cross-signal divergence detection reveals when
        related theses are splitting, suggesting a need for a decision.
        """
        divergences = []
        
        for i, id_a in enumerate(thesis_ids):
            for id_b in thesis_ids[i + 1:]:
                vec_a = self.analyze(id_a)
                vec_b = self.analyze(id_b)
                
                if vec_a.snapshot_count < 2 or vec_b.snapshot_count < 2:
                    continue
                
                # Compare velocity directions
                vel_a = sum(vec_a.velocity.values())
                vel_b = sum(vec_b.velocity.values())
                
                # Divergence: one going up, one going down
                if (vel_a > 0 and vel_b < 0) or (vel_a < 0 and vel_b > 0):
                    divergence_strength = abs(vel_a - vel_b) / 2
                    divergences.append({
                        "thesis_a": id_a,
                        "thesis_b": id_b,
                        "velocity_a": round(vel_a, 4),
                        "velocity_b": round(vel_b, 4),
                        "divergence_strength": round(divergence_strength, 4),
                        "direction": f"{id_a} {'rising' if vel_a > 0 else 'falling'} vs {id_b} {'rising' if vel_b > 0 else 'falling'}",
                    })
        
        return sorted(divergences, key=lambda d: d["divergence_strength"], reverse=True)
