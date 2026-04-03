"""SignalDrift Engine - Temporal Signal Dynamics.

The first engine that tracks how your strategic signals EVOLVE over time.
Every signal is a living entity with velocity, acceleration, and momentum.

Instead of snapshots, you get trajectories.
Instead of scores, you get motion vectors.
"""

from signalforge.drift.timeseries import TimeSeriesStore, SignalSnapshot
from signalforge.drift.analyzer import DriftAnalyzer
from signalforge.drift.classifier import SignalClassifier
from signalforge.drift.config import DriftConfig

__all__ = [
    "TimeSeriesStore",
    "SignalSnapshot",
    "DriftAnalyzer",
    "SignalClassifier",
    "DriftConfig",
]
