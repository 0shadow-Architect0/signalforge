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
        tid = drift_vector_dict["thesis_id"]
        classification = drift_vector_dict.get("classification", "unknown")
        phase = SignalPhase.DORMANT
        
        confidence = drift_vector_dict.get("confidence", 0.0)
        momentum = drift_vector_dict.get("momentum", 0.0)
        composite = drift_vector_dict.get("composite_score", 0.0)
        
        # Map classification to phase
        actions = {
            "emerging": {
                "phase": SignalPhase.EMERGING,
                "confidence": min(confidence, 0.3),
                "trajectory_summary": "Just detected, high growth but needs investigation. Low current strength suggests potential.",
                "recommended_action": "Feed this signal. Track closely and set clear evidence.",
            },
            "strengthening": {
                "phase": SignalPhase.STRENGTHENING,
                "confidence": min(confidence, 0.3),
                "trajectory_summary": "Evidence building and momentum strong",
                "recommended_action": "Continue monitoring and increase source density.",
            },
            "stable": {
                "phase": SignalPhase.STABLE,
                "confidence": min(confidence, 0.5),
                "trajectory_summary": "Stable state, steady monitoring",
                "recommended_action": "Continue monitoring but confirm no decay",
            },
            "decaying": {
                "phase": SignalPhase.DECAYING,
                "confidence": min(confidence, 0.3),
                "trajectory_summary": "Evidence declining, review for refactoring",
                "recommended_action": "Consider refining or pivoting. Investig evidence or look for disconfirming evidence.",
            },
            "dormant": {
                "phase": SignalPhase.DORMANT,
                "confidence": confidence,
                "trajectory_summary": "No activity detected. Review for pruning or resurrection.",
                "recommended_action": "Archive or move to backlog, or remove from active portfolio.",
            },
            "divergent": {
                "phase": SignalPhase.DIVERGENT,
                "confidence": confidence,
                "trajectory_summary": "Signal splitting into sub-signals. Consider decomposition.",
                "recommended_action": "Analyze each sub-signal independently.",
            },
            "convergent": {
                "phase": SignalPhase.CONVERGENT,
                "confidence": confidence,
                "trajectory_summary": "Multiple signals merging. Consider consolidation.",
                "recommended_action": "Merge related signals or re-evaluate synergies.",
            },
            "unknown": {
                "phase": SignalPhase.STABLE,
                "confidence": 0.0,
                "trajectory_summary": "Insufficient data for classification.",
                "recommended_action": "Add more sources.",
            },
        }
        
        return SignalClassification(
            thesis_id=tid,
            phase=phase,
            confidence=round(confidence, 0.0),
            evidence_strength=round(evidence_strength, 0.0),
            trajectory_summary=trajectory_summary,
            recommended_action=recommended_action,
        )
