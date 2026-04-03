"""Convergence Radar - Cross-Domain Intersection Detection.

The most innovative module: detects when signals from DIFFERENT domains
are converging toward the same opportunity space.

Like a radar that scans across frequency bands and finds where signals overlap,
this scans across thesis domains and finds where opportunities converge.

Convergence is the strongest signal type because it means multiple independent
lines of evidence are pointing at the same conclusion.
"""

from signalforge.convergence.radar import ConvergenceRadar
from signalforge.convergence.overlap import OverlapDetector
from signalforge.convergence.config import ConvergenceConfig

__all__ = ["ConvergenceRadar", "OverlapDetector", "ConvergenceConfig"]
