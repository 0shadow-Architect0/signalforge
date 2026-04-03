"""Adversarial Engine Configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AdversarialConfig:
    """Configuration for the Adversarial Thesis Engine.
    
    Controls how aggressively the system challenges your theses.
    """
    enabled: bool = True
    evidence_asymmetry_threshold: float = 3.0  # Flag when confirming:disconfirming > 3:1
    kill_criteria_alert_levels: dict = None  # Custom thresholds per alert level
    
    @classmethod
    def from_env(cls, **overrides) -> dict:
        return cls(
            enabled=overrides.get(
                "enabled",
                os.getenv("SF_ADVERSARIAL_ENABLED", "true").lower() == "true"
            ),
            evidence_asymmetry_threshold=float(overrides.get(
                "evidence_asymmetry_threshold",
                os.getenv("SF_ADVERSARIAL_ASYMMETRY", "3.0")
            )),
        )
