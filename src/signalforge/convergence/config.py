"""Convergence Radar Configuration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConvergenceConfig:
    """Configuration for the Convergence Radar."""
    
    # Minimum overlap score to consider two theses "converging"
    convergence_threshold: float = 0.3
    
    # Minimum number of shared dimensions for convergence
    min_shared_dimensions: int = 2
    
    # Dimensions to compare for convergence
    compare_dimensions: tuple = (
        "whitespace_score",
        "overlap_strength",
        "novelty",
        "urgency",
        "buildability",
        "founder_fit",
    )
    
    # Weight for each dimension in convergence scoring
    dimension_weights: dict | None = None
    
    def get_weights(self) -> dict:
        if self.dimension_weights:
            return self.dimension_weights
        return {d: 1.0 / len(self.compare_dimensions) for d in self.compare_dimensions}
