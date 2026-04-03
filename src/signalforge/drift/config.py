"""SignalDrift Configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DriftConfig:
    """Configuration for the SignalDrift Engine."""
    
    # Time windows for analysis (in days)
    short_window: int = 7
    medium_window: int = 30
    long_window: int = 90
    
    # Thresholds for classification
    emerging_velocity_threshold: float = 0.15
    decay_velocity_threshold: float = -0.1
    volatility_threshold: float = 0.3
    
    # Momentum = strength * velocity. Below this = dormant
    dormant_momentum_threshold: float = 0.05
    
    @classmethod
    def from_env(cls) -> "DriftConfig":
        return cls(
            short_window=int(os.getenv("SF_DRIFT_SHORT_WINDOW", "7")),
            medium_window=int(os.getenv("SF_DRIFT_MEDIUM_WINDOW", "30")),
            long_window=int(os.getenv("SF_DRIFT_LONG_WINDOW", "90")),
            emerging_velocity_threshold=float(os.getenv("SF_DRIFT_EMERGING_VEL", "0.15")),
            decay_velocity_threshold=float(os.getenv("SF_DRIFT_DECAY_VEL", "-0.1")),
        )
