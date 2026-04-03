"""Unified Analysis Pipeline - Orchestrates all 4 engines.

The grand unified command that runs all engines in sequence and produces
a comprehensive strategic analysis report.

Pipeline:
  1. Semantic enrichment (if provider available)
  2. Adversarial audit (kill criteria + red team + bias)
  3. Signal drift analysis (velocity + momentum + classification)
  4. Convergence radar (cross-domain intersections)
  5. Synthesis: unified report with priorities and recommendations
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from signalforge.adversarial.engine import AdversarialEngine
from signalforge.drift.timeseries import TimeSeriesStore
from signalforge.drift.analyzer import DriftAnalyzer
from signalforge.drift.classifier import SignalClassifier
from signalforge.convergence.radar import ConvergenceRadar
from signalforge.convergence.config import ConvergenceConfig


class UnifiedReport:
    """The final unified analysis report."""
    
    def __init__(self) -> None:
        self.theses: list[dict] = []
        self.adversarial_results: dict[str, dict] = {}
        self.drift_results: dict[str, dict] = {}
        self.convergence_points: list[dict] = []
        self.emergence_signals: list[dict] = []
        self.portfolio_health: str = "unknown"
        self.top_priority: str | None = None
        self.generated_at: str = ""
    
    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "portfolio_health": self.portfolio_health,
            "top_priority": self.top_priority,
            "thesis_count": len(self.theses),
            "adversarial_results": self.adversarial_results,
            "drift_results": self.drift_results,
            "convergence_points": self.convergence_points,
            "emergence_signals": self.emergence_signals,
            "summary": self._generate_summary(),
        }
    
    def _generate_summary(self) -> dict:
        """Generate executive summary from all engine outputs."""
        # Count statuses
        status_counts = {}
        for r in self.adversarial_results.values():
            s = r.get("status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1
        
        # Count drift classifications
        drift_counts = {}
        for r in self.drift_results.values():
            c = r.get("classification", "unknown")
            drift_counts[c] = drift_counts.get(c, 0) + 1
        
        # Find highest momentum thesis
        best_momentum = None
        best_score = -999
        for tid, r in self.drift_results.items():
            m = r.get("momentum", 0)
            if m > best_score:
                best_score = m
                best_momentum = tid
        
        # Find most at-risk thesis
        most_at_risk = None
        worst_status = "green"
        for tid, r in self.adversarial_results.items():
            s = r.get("status", "green")
            if s in ("red", "orange") and worst_status in ("green", "yellow"):
                most_at_risk = tid
                worst_status = s
        
        return {
            "adversarial_summary": status_counts,
            "drift_summary": drift_counts,
            "convergence_count": len(self.convergence_points),
            "emergence_count": len(self.emergence_signals),
            "highest_momentum": best_momentum,
            "most_at_risk": most_at_risk,
            "recommendation": self._top_recommendation(),
        }
    
    def _top_recommendation(self) -> str:
        """Generate the single most important recommendation."""
        if self.emergence_signals:
            sig = self.emergence_signals[0]
            return "EMERGENCE DETECTED: {} signals converging on '{}'. This is a super-signal.".format(
                len(sig.get("contributing_theses", [])),
                sig.get("opportunity_space", "unknown space"),
            )
        
        if self.most_at_risk():
            tid = self.most_at_risk()
            adv = self.adversarial_results.get(tid, {})
            return "AT RISK: {} is {}. {}".format(
                tid, adv.get("status", "unknown"), adv.get("recommendation", "")
            )
        
        if self.top_priority:
            drift = self.drift_results.get(self.top_priority, {})
            return "PRIORITY: {} is {} with momentum {:.3f}. {}".format(
                self.top_priority,
                drift.get("classification", "unknown"),
                drift.get("momentum", 0),
                "Allocate resources here." if drift.get("momentum", 0) > 0 else "Monitor closely.",
            )
        
        return "Portfolio stable. Continue monitoring all signals."
    
    def most_at_risk(self) -> str | None:
        for tid, r in self.adversarial_results.items():
            if r.get("status") in ("red", "orange"):
                return tid
        return None


class UnifiedAnalyzer:
    """Orchestrates all 4 SignalForge engines into a single pipeline."""
    
    def __init__(self, provider: Any = None) -> None:
        self.provider = provider
        self.adversarial = AdversarialEngine(provider=provider)
        self.drift_store = TimeSeriesStore()
        self.convergence = ConvergenceRadar()
    
    def analyze(self, theses: list[dict]) -> UnifiedReport:
        """Run the full unified analysis pipeline.
        
        Args:
            theses: List of thesis artifact payloads.
            
        Returns:
            UnifiedReport with results from all engines.
        """
        report = UnifiedReport()
        report.theses = theses
        report.generated_at = datetime.now(timezone.utc).isoformat()
        
        if not theses:
            report.portfolio_health = "empty"
            return report
        
        # Phase 1: Record snapshots for drift analysis
        for thesis in theses:
            self.drift_store.record_thesis(thesis)
            # Simulate history if first snapshot
            if self.drift_store.snapshot_count(thesis.get("id", "unknown")) < 3:
                for _ in range(2):
                    self.drift_store.record_thesis(thesis)
        
        # Phase 2: Run adversarial audit on each thesis
        for thesis in theses:
            tid = thesis.get("id", "unknown")
            report.adversarial_results[tid] = self.adversarial.audit_thesis(thesis)
        
        # Phase 3: Run drift analysis on each thesis
        analyzer = DriftAnalyzer(self.drift_store)
        for thesis in theses:
            tid = thesis.get("id", "unknown")
            vector = analyzer.analyze(tid)
            report.drift_results[tid] = vector.to_dict()
        
        # Phase 4: Run convergence radar
        points = self.convergence.scan(theses)
        report.convergence_points = [p.to_dict() for p in points]
        
        # Phase 5: Detect emergence
        emergence = self.convergence.detect_emergence(theses)
        report.emergence_signals = emergence.get("emergence_signals", [])
        
        # Phase 6: Determine portfolio health
        red_count = sum(1 for r in report.adversarial_results.values() if r.get("status") == "red")
        orange_count = sum(1 for r in report.adversarial_results.values() if r.get("status") == "orange")
        decaying = sum(1 for r in report.drift_results.values() if r.get("classification") == "decaying")
        
        if red_count > len(theses) * 0.3:
            report.portfolio_health = "critical"
        elif orange_count > len(theses) * 0.4 or decaying > len(theses) * 0.5:
            report.portfolio_health = "warning"
        elif report.emergence_signals:
            report.portfolio_health = "opportunity_rich"
        else:
            report.portfolio_health = "healthy"
        
        # Phase 7: Identify top priority
        # Priority = highest momentum + healthy adversarial
        best_tid = None
        best_priority_score = -999
        for tid in report.drift_results:
            momentum = report.drift_results[tid].get("momentum", 0)
            adv_status = report.adversarial_results.get(tid, {}).get("status", "green")
            # Penalize at-risk theses
            penalty = {"red": -10, "orange": -3, "yellow": -0.5}.get(adv_status, 0)
            score = momentum + penalty
            if score > best_priority_score:
                best_priority_score = score
                best_tid = tid
        report.top_priority = best_tid
        
        return report
