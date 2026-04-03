"""Semantic Enrichment Functions.

These functions add LLM-powered deep understanding ON TOP of the existing
deterministic analysis. They never replace it - they enrich it.

Design principle: Every function returns None when no LLM is available,
and the system falls back to deterministic-only output seamlessly.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .prompts import (
    CALIBRATION_SYSTEM,
    CALIBRATION_USER,
    COMPARISON_ENRICHMENT_SYSTEM,
    COMPARISON_ENRICHMENT_USER,
    CONTRADICTION_ENRICHMENT_SYSTEM,
    CONTRADICTION_ENRICHMENT_USER,
    SOURCE_ENRICHMENT_SYSTEM,
    SOURCE_ENRICHMENT_USER,
    WHITESPACE_ENRICHMENT_SYSTEM,
    WHITESPACE_ENRICHMENT_USER,
)

logger = logging.getLogger(__name__)


def _sources_json(sources: list[dict]) -> str:
    """Format sources for prompt inclusion."""
    items = []
    for s in sources:
        items.append(
            {
                "id": s.get("id"),
                "title": s.get("title"),
                "type": s.get("type"),
                "summary": s.get("summary") or s.get("strategic_summary") or "N/A",
                "signals": s.get("signals", []),
                "domain_cues": s.get("domain_cues", []),
                "capability_hints": s.get("capability_hints", []),
            }
        )
    return json.dumps(items, indent=2, ensure_ascii=False)


def enrich_source(
    source_payload: dict,
    provider: Any,
) -> dict | None:
    """Deep enrichment of a single source.

    Adds: strategic summary, extracted signals, domain classification,
    capability map, opportunity hints, risk indicators, freshness assessment.

    Returns None if provider unavailable (graceful degradation).
    """
    if not provider.available():
        return None

    user_prompt = SOURCE_ENRICHMENT_USER.format(
        title=source_payload.get("title", "Untitled"),
        source_type=source_payload.get("type", "unknown"),
        summary=source_payload.get("summary") or "No summary",
        uri=source_payload.get("uri") or "N/A",
        tags=", ".join(source_payload.get("tags", [])),
        signals=", ".join(source_payload.get("signals", [])),
        domain_cues=", ".join(source_payload.get("domain_cues", [])),
        capability_hints=", ".join(source_payload.get("capability_hints", [])),
    )

    result = provider.complete_structured(
        system=SOURCE_ENRICHMENT_SYSTEM,
        user=user_prompt,
        expected_keys=["strategic_summary", "extracted_signals", "domain_classification"],
        temperature=0.3,
    )

    if result is None:
        return None

    return {
        "semantic_strategic_summary": result.get("strategic_summary"),
        "semantic_signals": result.get("extracted_signals", []),
        "semantic_domains": result.get("domain_classification", []),
        "semantic_capabilities": result.get("capability_map", []),
        "semantic_opportunity_hints": result.get("opportunity_hints", []),
        "semantic_risk_indicators": result.get("risk_indicators", []),
        "semantic_freshness": result.get("freshness_assessment"),
        "semantic_novelty": result.get("novelty_assessment"),
        "semantic_builder_relevance": result.get("builder_relevance"),
    }


def enrich_comparison(
    sources: list[dict],
    deterministic_comparison: dict,
    provider: Any,
) -> dict | None:
    """Deep cross-source comparison beyond keyword overlap.

    Adds: conceptual overlap, complementary zones, hidden connections,
    divergence points, synthesis opportunity.

    Returns None if provider unavailable.
    """
    if not provider.available() or len(sources) < 2:
        return None

    user_prompt = COMPARISON_ENRICHMENT_USER.format(
        sources_json=_sources_json(sources),
        shared_capabilities=", ".join(deterministic_comparison.get("shared_capabilities", [])),
        differentiation_zones=", ".join(deterministic_comparison.get("differentiation_zones", [])),
        overlap_strength=deterministic_comparison.get("overlap_strength", 0.0),
    )

    result = provider.complete_structured(
        system=COMPARISON_ENRICHMENT_SYSTEM,
        user=user_prompt,
        expected_keys=["conceptual_overlap", "complementary_zones"],
        temperature=0.3,
    )

    if result is None:
        return None

    return {
        "semantic_conceptual_overlap": result.get("conceptual_overlap", []),
        "semantic_complementary_zones": result.get("complementary_zones", []),
        "semantic_hidden_connections": result.get("hidden_connections", []),
        "semantic_divergence_points": result.get("divergence_points", []),
        "semantic_synthesis_opportunity": result.get("synthesis_opportunity"),
        "semantic_combined_novelty": result.get("combined_novelty"),
    }


def enrich_contradictions(
    sources: list[dict],
    deterministic_contradictions: dict,
    deterministic_comparison: dict,
    provider: Any,
) -> dict | None:
    """Deep contradiction detection beyond token divergence.

    Adds: logical contradictions, assumption conflicts, creative tensions.

    Returns None if provider unavailable.
    """
    if not provider.available() or len(sources) < 2:
        return None

    user_prompt = CONTRADICTION_ENRICHMENT_USER.format(
        sources_json=_sources_json(sources),
        detected_count=deterministic_contradictions.get("contradiction_count", 0),
        differentiation_zones=", ".join(
            deterministic_comparison.get("differentiation_zones", [])
        ),
    )

    result = provider.complete_structured(
        system=CONTRADICTION_ENRICHMENT_SYSTEM,
        user=user_prompt,
        expected_keys=["logical_contradictions", "assumption_conflicts"],
        temperature=0.3,
    )

    if result is None:
        return None

    return {
        "semantic_logical_contradictions": result.get("logical_contradictions", []),
        "semantic_assumption_conflicts": result.get("assumption_conflicts", []),
        "semantic_creative_tensions": result.get("creative_tensions", []),
    }


def enrich_whitespace(
    sources: list[dict],
    deterministic_whitespace: dict,
    provider: Any,
) -> dict | None:
    """Deep whitespace discovery beyond formula-based scoring.

    Adds: specific whitespace opportunities with entry wedges,
    emerging patterns, strategic wedge identification.

    Returns None if provider unavailable.
    """
    if not provider.available() or not sources:
        return None

    user_prompt = WHITESPACE_ENRICHMENT_USER.format(
        sources_json=_sources_json(sources),
        wedge_statement=deterministic_whitespace.get("wedge_statement", "N/A"),
        category_pressure=deterministic_whitespace.get("category_pressure", "N/A"),
        whitespace_score=deterministic_whitespace.get("whitespace_score", 0.0),
    )

    result = provider.complete_structured(
        system=WHITESPACE_ENRICHMENT_SYSTEM,
        user=user_prompt,
        expected_keys=["whitespace_opportunities"],
        temperature=0.4,
    )

    if result is None:
        return None

    return {
        "semantic_whitespace_opportunities": result.get("whitespace_opportunities", []),
        "semantic_emerging_pattern": result.get("emerging_pattern"),
        "semantic_strategic_wedge": result.get("strategic_wedge"),
    }


def calibrate_confidence(
    sources: list[dict],
    scores: dict,
    provider: Any,
) -> dict | None:
    """Semantic confidence calibration.

    Innovation: The LLM reviews the deterministic scores against the actual
    content and suggests adjustments. This creates a feedback loop between
    heuristic metrics and semantic understanding.

    Returns None if provider unavailable.
    """
    if not provider.available() or not sources:
        return None

    user_prompt = CALIBRATION_USER.format(
        sources_json=_sources_json(sources),
        overlap_strength=scores.get("overlap_strength", 0.0),
        whitespace_score=scores.get("whitespace_score", 0.0),
        novelty=scores.get("novelty", 0.0),
        urgency=scores.get("urgency", 0.0),
        founder_fit=scores.get("founder_fit", 0.0),
        buildability=scores.get("buildability", 0.0),
        strategic_leverage=scores.get("strategic_leverage", 0.0),
    )

    result = provider.complete_structured(
        system=CALIBRATION_SYSTEM,
        user=user_prompt,
        expected_keys=["overall_assessment", "score_adjustments"],
        temperature=0.2,
    )

    if result is None:
        return None

    adjustments = result.get("score_adjustments", {})
    calibrated_scores = {}
    for key, adj in adjustments.items():
        if isinstance(adj, dict) and "adjustment" in adj:
            original = scores.get(key, 0.0)
            delta = adj["adjustment"]
            calibrated_scores[key] = {
                "original": original,
                "adjustment": delta,
                "calibrated": round(max(0.0, min(10.0, original + delta)), 2),
                "reason": adj.get("reason", ""),
            }

    return {
        "overall_assessment": result.get("overall_assessment"),
        "calibrated_scores": calibrated_scores,
        "key_concerns": result.get("key_concerns", []),
        "key_agreements": result.get("key_agreements", []),
    }
