"""Semantic Intelligence Layer for SignalForge.

Adds LLM-powered deep understanding on top of deterministic analysis.
Gracefully degrades to heuristic-only mode when no provider is configured.

Key innovations:
- Evidence Chain Extraction: extracts argument structure from sources
- Semantic Confidence Calibration: LLM refines deterministic scores
- Cross-Source Synthesis: discovers connections token analysis misses
"""

from signalforge.semantic.provider import LLMProvider, OpenAIProvider, NoOpProvider
from signalforge.semantic.enricher import (
    enrich_source,
    enrich_comparison,
    enrich_contradictions,
    enrich_whitespace,
    calibrate_confidence,
)
from signalforge.semantic.evidence import extract_evidence_chain, EvidenceChain
from signalforge.semantic.config import SemanticConfig

__all__ = [
    "LLMProvider",
    "OpenAIProvider",
    "NoOpProvider",
    "SemanticConfig",
    "enrich_source",
    "enrich_comparison",
    "enrich_contradictions",
    "enrich_whitespace",
    "calibrate_confidence",
    "extract_evidence_chain",
    "EvidenceChain",
]
