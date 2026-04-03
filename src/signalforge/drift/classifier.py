"""Signal Classifier - Classifies signal lifecycle state.

EMERGING -> STRENGTHENING -> STABLE -> DECAYING -> DORMANT
DIVERGENT -> CONVERGENT
"""

from __future__ import annotations
from enum import Enum
from pydantic import BaseModel


class SignalPhase(str, Enum):
    EMERGING = "emerging"
    STRENGTHENING = "strengthening"
    STABLE = "stable"
    DECAYING = "decaying"
    DORMANT = "dormant"
    DIVERGENT = "divergent"
    CONVERGENT = "convergent"


class SignalClassification(BaseModel):
    thesis_id: str
    phase: SignalPhase
    confidence: float
    evidence_strength: float
    trajectory_summary: str
    recommended_action: str
    
    def to_dict(self) -> dict:
        return self.model_dump(mode="json")


class SignalClassifier:
    @staticmethod
    def classify(drift_vector_dict: dict) -> SignalClassification:
        tid = drift_vector_dict.get("thesis_id", "unknown")
        classification = drift_vector_dict.get("classification", "unknown")
        confidence = drift_vector_dict.get("confidence", 0.0)
        momentum = drift_vector_dict.get("momentum", 0.0)
        volatility = drift_vector_dict.get("volatility", 0.0)
        velocity = drift_vector_dict.get("velocity", {})
        snapshots = drift_vector_dict.get("snapshot_count", 0)

        # Map drift classification to phase
        phase_map = {
            "emerging": SignalPhase.EMERGING,
            "strengthening": SignalPhase.STRENGTHENING,
            "stable": SignalPhase.STABLE,
            "decaying": SignalPhase.DECAYING,
            "dormant": SignalPhase.DORMANT,
            "volatile": SignalPhase.DIVERGENT,
            "unknown": SignalPhase.STABLE,
        }
        phase = phase_map.get(classification, SignalPhase.STABLE)

        # Compute evidence strength from momentum + snapshots
        evidence_strength = min(1.0, max(0.0, 0.3 + momentum * 0.01 + snapshots * 0.05))

        # Trajectory summary and recommended action
        summaries = {
            "emerging": ("Just detected, high growth but needs investigation.", "Feed this signal. Track closely and gather evidence."),
            "strengthening": ("Evidence building and momentum strong.", "Continue monitoring. Increase source density."),
            "stable": ("Stable state, steady monitoring.", "Continue monitoring. Watch for velocity changes."),
            "decaying": ("Evidence declining. Review for pivot.", "Consider refining, pivoting, or reducing allocation."),
            "dormant": ("No meaningful activity detected.", "Archive or move to backlog."),
            "volatile": ("High volatility, unpredictable trajectory.", "Investigate noise sources. Wait for stabilization."),
        }
        default = ("Insufficient data for classification.", "Add more sources and snapshots.")
        trajectory_summary, recommended_action = summaries.get(classification, default)

        return SignalClassification(
            thesis_id=tid,
            phase=phase,
            confidence=round(confidence, 2),
            evidence_strength=round(evidence_strength, 3),
            trajectory_summary=trajectory_summary,
            recommended_action=recommended_action,
        )
