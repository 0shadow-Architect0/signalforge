"""Overlap Detector - Finds shared dimensions between theses.

Computes multi-dimensional similarity between thesis payloads
across whitespace, opportunity, and comparison dimensions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class OverlapResult(BaseModel):
    """Result of overlap detection between two theses."""
    thesis_a: str
    thesis_b: str
    shared_dimensions: list[str]
    dimension_scores: dict[str, float]
    overlap_score: float
    convergence_type: str  # complementary, competing, orthogonal, synergistic
    
    def to_dict(self) -> dict:
        return self.model_dump(mode="json")


class OverlapDetector:
    """Detects multi-dimensional overlap between thesis payloads."""
    
    @staticmethod
    def detect(thesis_a: dict, thesis_b: dict) -> OverlapResult:
        """Compute overlap between two thesis payloads."""
        id_a = thesis_a.get("id", "a")
        id_b = thesis_b.get("id", "b")
        
        # Extract score vectors
        opp_a = thesis_a.get("opportunity", {}).get("scores", {})
        opp_b = thesis_b.get("opportunity", {}).get("scores", {})
        ws_a = thesis_a.get("whitespace", {})
        ws_b = thesis_b.get("whitespace", {})
        comp_a = thesis_a.get("comparison", {})
        comp_b = thesis_b.get("comparison", {})
        
        # Compare dimensions
        dimension_scores = {}
        shared_dimensions = []
        
        # Opportunity score similarity
        for key in set(list(opp_a.keys()) + list(opp_b.keys())):
            val_a = float(opp_a.get(key, 0) or 0)
            val_b = float(opp_b.get(key, 0) or 0)
            similarity = 1.0 - abs(val_a - val_b) / 10.0
            dimension_scores[key] = round(similarity, 3)
            if similarity > 0.6:
                shared_dimensions.append(key)
        
        # Whitespace similarity
        ws_score_a = float(ws_a.get("whitespace_score", 0) or 0)
        ws_score_b = float(ws_b.get("whitespace_score", 0) or 0)
        ws_similarity = 1.0 - abs(ws_score_a - ws_score_b) / 10.0
        dimension_scores["whitespace_score"] = round(ws_similarity, 3)
        if ws_similarity > 0.6:
            shared_dimensions.append("whitespace_score")
        
        # Overlap strength similarity
        ol_a = float(comp_a.get("overlap_strength", 0) or 0)
        ol_b = float(comp_b.get("overlap_strength", 0) or 0)
        ol_similarity = 1.0 - abs(ol_a - ol_b)
        dimension_scores["overlap_strength"] = round(ol_similarity, 3)
        if ol_similarity > 0.6:
            shared_dimensions.append("overlap_strength")
        
        # Shared capabilities
        caps_a = set(comp_a.get("shared_capabilities", []))
        caps_b = set(comp_b.get("shared_capabilities", []))
        shared_caps = caps_a & caps_b
        if shared_caps:
            dimension_scores["shared_capabilities"] = 1.0
            shared_dimensions.append("shared_capabilities")
        
        # Differentiation zones overlap
        diff_a = set(comp_a.get("differentiation_zones", []))
        diff_b = set(comp_b.get("differentiation_zones", []))
        shared_diff = diff_a & diff_b
        if shared_diff:
            dimension_scores["shared_differentiation"] = 1.0
            shared_dimensions.append("shared_differentiation")
        
        # Overall overlap score
        overlap_score = sum(dimension_scores.values()) / max(1, len(dimension_scores))
        
        # Determine convergence type
        convergence_type = OverlapDetector._classify_convergence(
            thesis_a, thesis_b, overlap_score, shared_dimensions
        )
        
        return OverlapResult(
            thesis_a=id_a,
            thesis_b=id_b,
            shared_dimensions=shared_dimensions,
            dimension_scores=dimension_scores,
            overlap_score=round(overlap_score, 3),
            convergence_type=convergence_type,
        )
    
    @staticmethod
    def _classify_convergence(
        thesis_a: dict,
        thesis_b: dict,
        overlap_score: float,
        shared_dims: list[str],
    ) -> str:
        """Classify the type of convergence between two theses."""
        if overlap_score < 0.3:
            return "orthogonal"
        
        # Check if they share whitespace/wedge
        ws_a = thesis_a.get("whitespace", {}).get("wedge_statement", "")
        ws_b = thesis_b.get("whitespace", {}).get("wedge_statement", "")
        
        caps_a = set(thesis_a.get("comparison", {}).get("shared_capabilities", []))
        caps_b = set(thesis_b.get("comparison", {}).get("shared_capabilities", []))
        
        shared_caps = caps_a & caps_b
        all_caps = caps_a | caps_b
        
        # Synergistic: high overlap + complementary capabilities
        if shared_caps and len(shared_caps) < len(all_caps):
            return "synergistic"
        
        # Competing: same capabilities, same space
        if shared_caps and len(shared_caps) == len(all_caps) and len(all_caps) > 0:
            return "competing"
        
        # Complementary: different capabilities but high overlap
        if overlap_score > 0.5 and not shared_caps:
            return "complementary"
        
        return "orthogonal"
