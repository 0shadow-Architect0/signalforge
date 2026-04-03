"""Convergence Radar - Scans for cross-domain signal convergence.

The innovation: most tools analyze theses in isolation. This one finds
where MULTIPLE independent theses are pointing at the same opportunity.

When 3+ signals converge on the same space, that's a super-signal
worth 10x more than any individual signal.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from signalforge.convergence.overlap import OverlapDetector, OverlapResult
from signalforge.convergence.config import ConvergenceConfig


class ConvergencePoint:
    """A detected convergence point where multiple signals meet."""
    
    def __init__(
        self,
        thesis_ids: list[str],
        overlap_results: list[OverlapResult],
        convergence_score: float,
        convergence_type: str,
        opportunity_space: str,
    ) -> None:
        self.thesis_ids = thesis_ids
        self.overlap_results = overlap_results
        self.convergence_score = convergence_score
        self.convergence_type = convergence_type
        self.opportunity_space = opportunity_space
    
    def to_dict(self) -> dict:
        return {
            "thesis_ids": self.thesis_ids,
            "pairwise_overlaps": [r.to_dict() for r in self.overlap_results],
            "convergence_score": round(self.convergence_score, 3),
            "convergence_type": self.convergence_type,
            "opportunity_space": self.opportunity_space,
            "signal_strength": self._signal_strength(),
            "detected_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def _signal_strength(self) -> str:
        """Classify the overall signal strength."""
        n = len(self.thesis_ids)
        score = self.convergence_score
        if n >= 4 and score > 0.6:
            return "supersignal"
        elif n >= 3 and score > 0.5:
            return "strong"
        elif n >= 2 and score > 0.4:
            return "moderate"
        else:
            return "weak"


class ConvergenceRadar:
    """Scans a portfolio of theses for convergence patterns.
    
    Usage:
        radar = ConvergenceRadar()
        points = radar.scan(theses)
        for point in points:
            print(f"{point.signal_strength}: {point.thesis_ids}")
    """
    
    def __init__(self, config: ConvergenceConfig | None = None) -> None:
        self.config = config or ConvergenceConfig()
        self.detector = OverlapDetector()
    
    def scan(self, theses: list[dict]) -> list[ConvergencePoint]:
        """Scan all theses for convergence patterns.
        
        Returns convergence points sorted by score (highest first).
        """
        if len(theses) < 2:
            return []
        
        # Step 1: Compute pairwise overlaps
        pairwise: dict[tuple[str, str], OverlapResult] = {}
        for i, a in enumerate(theses):
            for b in theses[i + 1:]:
                result = self.detector.detect(a, b)
                key = (result.thesis_a, result.thesis_b)
                pairwise[key] = result
        
        # Step 2: Find convergence clusters (groups of theses with high mutual overlap)
        convergence_points = []
        
        # Find pairs first
        significant_pairs = {
            k: v for k, v in pairwise.items()
            if v.overlap_score >= self.config.convergence_threshold
        }
        
        if not significant_pairs:
            return []
        
        # Build adjacency for clustering
        adjacency: dict[str, set[str]] = {}
        for (a_id, b_id), result in significant_pairs.items():
            adjacency.setdefault(a_id, set()).add(b_id)
            adjacency.setdefault(b_id, set()).add(a_id)
        
        # Find connected components (clusters)
        visited = set()
        clusters = []
        for node in adjacency:
            if node in visited:
                continue
            cluster = set()
            stack = [node]
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                cluster.add(current)
                stack.extend(adjacency.get(current, set()) - visited)
            clusters.append(sorted(cluster))
        
        # Step 3: Build convergence points from clusters
        theses_by_id = {t.get("id"): t for t in theses}
        
        for cluster_ids in clusters:
            if len(cluster_ids) < 2:
                continue
            
            # Get pairwise results for this cluster
            cluster_overlaps = []
            for i, a_id in enumerate(cluster_ids):
                for b_id in cluster_ids[i + 1:]:
                    key = (a_id, b_id)
                    rev_key = (b_id, a_id)
                    result = pairwise.get(key) or pairwise.get(rev_key)
                    if result:
                        cluster_overlaps.append(result)
            
            # Compute average convergence score
            scores = [r.overlap_score for r in cluster_overlaps]
            avg_score = sum(scores) / max(1, len(scores))
            
            # Determine overall convergence type
            type_counts = {}
            for r in cluster_overlaps:
                t = r.convergence_type
                type_counts[t] = type_counts.get(t, 0) + 1
            dominant_type = max(type_counts, key=type_counts.get) if type_counts else "orthogonal"
            
            # Describe opportunity space
            all_ws = []
            for tid in cluster_ids:
                t = theses_by_id.get(tid, {})
                ws = t.get("whitespace", {}).get("wedge_statement", "")
                if ws:
                    all_ws.append(ws)
            opportunity = " | ".join(all_ws[:3]) if all_ws else f"Shared space across {len(cluster_ids)} theses"
            
            convergence_points.append(ConvergencePoint(
                thesis_ids=cluster_ids,
                overlap_results=cluster_overlaps,
                convergence_score=avg_score,
                convergence_type=dominant_type,
                opportunity_space=opportunity,
            ))
        
        # Sort by convergence score descending
        convergence_points.sort(key=lambda p: p.convergence_score, reverse=True)
        return convergence_points
    
    def detect_emergence(self, theses: list[dict]) -> dict:
        """Detect emergence: when convergence + drift suggest a NEW opportunity.
        
        This is the meta-signal: when signals converge AND are strengthening,
        a new opportunity space is emerging that none of the individual theses
        captured alone.
        """
        points = self.scan(theses)
        
        emergence_signals = []
        for point in points:
            if point.convergence_score > 0.5 and len(point.thesis_ids) >= 3:
                emergence_signals.append({
                    "type": "emergent_opportunity",
                    "convergence_score": point.convergence_score,
                    "contributing_theses": point.thesis_ids,
                    "opportunity_space": point.opportunity_space,
                    "signal_strength": point._signal_strength(),
                })
        
        return {
            "emergence_signals": emergence_signals,
            "total_convergence_points": len(points),
            "strong_signals": sum(1 for p in points if p._signal_strength() in ("strong", "supersignal")),
            "scanned_at": datetime.now(timezone.utc).isoformat(),
        }
