from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from itertools import combinations
from statistics import mean
from typing import Iterable

from .models import OpportunityScores, Source

STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
    "your",
    "their",
    "this",
    "that",
    "these",
    "those",
    "our",
    "its",
    "be",
    "are",
    "was",
    "were",
}


def strategic_tokens(sources: Iterable[Source]) -> list[str]:
    tokens: list[str] = []
    for source in sources:
        chunks = [source.title or "", source.summary or "", source.strategic_summary or "", source.uri or ""]
        chunks.extend(source.tags)
        chunks.extend(source.signals)
        chunks.extend(source.domain_cues)
        chunks.extend(source.capability_hints)
        for chunk in chunks:
            normalized = chunk.replace("/", " ").replace("_", " ").replace("-", " ")
            for raw in normalized.split():
                token = raw.strip().lower().strip(".,:;()[]{}!?'\"")
                if token and token not in STOPWORDS and len(token) > 2:
                    tokens.append(token)
    return tokens


def compare_sources(sources: list[Source]) -> dict:
    token_counts = Counter(strategic_tokens(sources))
    repeated = [token for token, count in token_counts.items() if count >= 2]
    unique = [token for token, count in token_counts.items() if count == 1]
    shared_capabilities = repeated[:8]
    differentiation_zones = unique[:8]
    source_types = sorted({source.type for source in sources})
    freshness_profile = {
        "average": round(mean(source.freshness_score for source in sources), 2) if sources else 0.0,
        "highest": round(max((source.freshness_score for source in sources), default=0.0), 2),
        "lowest": round(min((source.freshness_score for source in sources), default=0.0), 2),
    }
    domain_cues = sorted({cue for source in sources for cue in source.domain_cues})
    capability_hints = sorted({hint for source in sources for hint in source.capability_hints})
    overlap_strength = round(min(0.95, len(shared_capabilities) / max(2, len(token_counts))), 2) if token_counts else 0.0
    comparison_summary = (
        f"The source set converges around {', '.join(shared_capabilities[:3]) or 'a coherent strategic pattern'}, "
        f"preserves differentiation in {', '.join(differentiation_zones[:3]) or 'specific implementation details'}, "
        f"and carries freshness avg {freshness_profile['average']} across domain cues {', '.join(domain_cues[:3]) or 'general strategy'}."
    )
    return {
        "source_ids": [source.id for source in sources],
        "source_types": source_types,
        "shared_capabilities": shared_capabilities,
        "differentiation_zones": differentiation_zones,
        "overlap_strength": overlap_strength,
        "freshness_profile": freshness_profile,
        "domain_cues": domain_cues,
        "capability_hints": capability_hints,
        "comparison_summary": comparison_summary,
    }


def extract_contradictions(sources: list[Source], comparison: dict) -> dict:
    repeated = set(comparison.get("shared_capabilities", []))
    differentiated = comparison.get("differentiation_zones", [])
    contradictions = []
    for token in differentiated[:4]:
        if token not in repeated:
            contradictions.append(
                f"The source set converges on shared strategic structure, but diverges around '{token}', creating an unresolved implementation or market posture tension."
            )
    severity = "high" if len(contradictions) >= 3 else "medium" if contradictions else "low"
    return {
        "contradictions": contradictions,
        "contradiction_count": len(contradictions),
        "severity": severity,
    }


def whitespace_from_comparison(comparison: dict) -> dict:
    shared = comparison["shared_capabilities"]
    diff = comparison["differentiation_zones"]
    freshness_average = float(comparison.get("freshness_profile", {}).get("average", 0.0) or 0.0)
    dominant_domain = ", ".join(comparison.get("domain_cues", [])[:2]) or "general strategy"
    wedge = (
        f"Combine {', '.join(shared[:2]) or 'shared strategic structure'} with "
        f"{', '.join(diff[:2]) or 'underused differentiated implementation'} inside the domain of {dominant_domain} to define a sharper category edge."
    )
    category_pressure = "rising" if comparison["overlap_strength"] >= 0.25 else "fragmented"
    whitespace_score = round(
        7.0 + min(2.5, len(diff) * 0.15 + (1 - comparison["overlap_strength"]) * 1.5 + freshness_average * 0.25),
        2,
    )
    return {
        "wedge_statement": wedge,
        "category_pressure": category_pressure,
        "whitespace_score": whitespace_score,
        "recommended_motion": "advance" if whitespace_score >= 8.0 else "combine",
    }


def score_opportunity(sources: list[Source], comparison: dict, whitespace: dict) -> OpportunityScores:
    source_type_diversity = len(comparison["source_types"])
    shared = len(comparison["shared_capabilities"])
    diff = len(comparison["differentiation_zones"])
    domain_strength = len(comparison.get("domain_cues", []))
    capability_depth = len(comparison.get("capability_hints", []))
    freshness_average = float(comparison.get("freshness_profile", {}).get("average", 0.0) or 0.0)
    novelty = round(min(9.5, 6.6 + diff * 0.2 + source_type_diversity * 0.22 + capability_depth * 0.07), 1)
    urgency = round(min(9.5, 6.5 + source_type_diversity * 0.25 + freshness_average * 1.1), 1)
    founder_fit = round(min(9.5, 7.0 + shared * 0.16 + domain_strength * 0.08), 1)
    buildability = round(min(9.3, 6.7 + max(0, shared - diff * 0.1) * 0.16 + capability_depth * 0.06), 1)
    monetization = round(min(9.4, 6.9 + source_type_diversity * 0.18 + shared * 0.07 + domain_strength * 0.08), 1)
    strategic_leverage = round(min(9.7, mean([novelty, urgency, founder_fit, monetization]) + 0.35), 1)
    return OpportunityScores(
        novelty=novelty,
        urgency=urgency,
        founder_fit=founder_fit,
        buildability=buildability,
        monetization=monetization,
        strategic_leverage=strategic_leverage,
    )


def classify_source_freshness(score: float) -> str:
    if score >= 0.85:
        return "hot"
    if score >= 0.7:
        return "warm"
    if score >= 0.55:
        return "cool"
    return "stale"


def _parse_timestamp(raw: str | None) -> datetime | None:
    if not raw:
        return None
    candidate = raw.strip()
    if not candidate:
        return None
    normalized = candidate[:-1] + "+00:00" if candidate.endswith("Z") else candidate
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(candidate)
        except (TypeError, ValueError, IndexError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def estimate_source_age_days(source_payload: dict, now: datetime | None = None) -> int | None:
    now = now or datetime.now(timezone.utc)
    metadata = source_payload.get("metadata", {}) or {}
    candidate_values = [
        metadata.get("updated_at"),
        metadata.get("published_at"),
        metadata.get("last_modified"),
        source_payload.get("updated_at"),
        source_payload.get("captured_at"),
        source_payload.get("created_at"),
    ]
    for raw in candidate_values:
        parsed = _parse_timestamp(str(raw)) if raw else None
        if parsed is None:
            continue
        delta = now - parsed
        return max(0, int(delta.total_seconds() // 86400))
    return None


def infer_provenance_quality(source_payload: dict) -> str:
    metadata = source_payload.get("metadata", {}) or {}
    source_type = source_payload.get("type")
    if source_type == "repo" and metadata.get("github_owner") and metadata.get("github_repo"):
        return "verified-repository"
    if source_type == "paper" and metadata.get("paper_source") == "arxiv":
        return "research-archive"
    if source_type == "article" and metadata.get("hostname"):
        return "published-web"
    if source_payload.get("uri"):
        return "direct-url"
    return "local-note"


def source_credibility_score(source_payload: dict) -> float:
    provenance_quality = infer_provenance_quality(source_payload)
    base = {
        "verified-repository": 0.92,
        "research-archive": 0.88,
        "published-web": 0.74,
        "direct-url": 0.68,
        "local-note": 0.58,
    }.get(provenance_quality, 0.6)
    metadata = source_payload.get("metadata", {}) or {}
    if metadata.get("stars"):
        try:
            stars = int(metadata["stars"])
        except (TypeError, ValueError):
            stars = 0
        if stars >= 10000:
            base += 0.05
        elif stars >= 1000:
            base += 0.03
    if source_payload.get("author"):
        base += 0.02
    if source_payload.get("uri"):
        base += 0.02
    return round(min(0.98, base), 2)


def _source_support_features(source_payload: dict) -> set[str]:
    features: set[str] = set()
    for key in ("signals", "domain_cues", "capability_hints", "tags"):
        for raw in source_payload.get(key, []) or []:
            normalized = str(raw).strip().lower()
            if normalized:
                features.add(normalized)
    return features


def evidence_convergence(sources: list[dict]) -> dict:
    if not sources:
        return {
            "convergence_score": 0.0,
            "convergence_state": "weak",
            "average_pairwise_overlap": 0.0,
            "shared_support_features": [],
            "cross_type_support_features": [],
            "convergence_summary": "No source bundle exists yet, so there is no convergence to evaluate.",
        }

    source_type_count = len({source.get("type") or "unknown" for source in sources})
    feature_counts: Counter[str] = Counter()
    feature_type_support: dict[str, set[str]] = {}
    feature_sets: list[set[str]] = []

    for source in sources:
        source_type = str(source.get("type") or "unknown")
        features = _source_support_features(source)
        feature_sets.append(features)
        for feature in features:
            feature_counts[feature] += 1
            feature_type_support.setdefault(feature, set()).add(source_type)

    pairwise_overlap_values: list[float] = []
    for left, right in combinations(feature_sets, 2):
        union = left | right
        overlap = (len(left & right) / len(union)) if union else 0.0
        pairwise_overlap_values.append(overlap)
    average_pairwise_overlap = round(mean(pairwise_overlap_values), 2) if pairwise_overlap_values else 1.0

    shared_features = sorted(
        [feature for feature, count in feature_counts.items() if count >= 2],
        key=lambda feature: (-feature_counts[feature], -len(feature_type_support.get(feature, set())), feature),
    )
    cross_type_support_features = [
        feature for feature in shared_features if len(feature_type_support.get(feature, set())) >= 2
    ]

    repeated_feature_score = min(0.35, len(shared_features) * 0.06)
    cross_type_support_score = min(0.25, len(cross_type_support_features) * 0.08)
    diversity_bonus = min(0.1, max(0, source_type_count - 1) * 0.05)
    convergence_score = round(
        min(1.0, average_pairwise_overlap * 0.3 + repeated_feature_score + cross_type_support_score + diversity_bonus),
        2,
    )

    if convergence_score >= 0.7:
        convergence_state = "strong"
    elif convergence_score >= 0.45:
        convergence_state = "moderate"
    else:
        convergence_state = "weak"

    convergence_summary = (
        f"Sources repeat {len(shared_features)} strategic support features with average pairwise overlap "
        f"{average_pairwise_overlap} across {source_type_count} source types, yielding {convergence_state} convergence."
    )

    return {
        "convergence_score": convergence_score,
        "convergence_state": convergence_state,
        "average_pairwise_overlap": average_pairwise_overlap,
        "shared_support_features": shared_features[:8],
        "cross_type_support_features": cross_type_support_features[:8],
        "convergence_summary": convergence_summary,
    }


def schedule_review_after(
    bundle_health: str,
    freshness_score: float,
    contradiction_score: float,
    average_source_age_days: int | None,
    now: datetime | None = None,
) -> str:
    now = now or datetime.now(timezone.utc)
    if bundle_health == "expired":
        offset_days = 3
    elif bundle_health == "fragile":
        offset_days = 7
    elif contradiction_score >= 0.3 or freshness_score < 0.75:
        offset_days = 14
    elif average_source_age_days is not None and average_source_age_days >= 45:
        offset_days = 21
    else:
        offset_days = 30
    return (now + timedelta(days=offset_days)).date().isoformat()


def audit_evidence_bundle(
    thesis_payload: dict,
    sources: list[dict],
    decisions: list[dict],
    execution_artifacts: list[dict],
) -> dict:
    contradiction_count = int(thesis_payload.get("contradictions", {}).get("contradiction_count", 0) or 0)
    contradiction_severity = thesis_payload.get("contradictions", {}).get("severity", "low")
    freshness_values = [float(source.get("freshness_score", 0.0) or 0.0) for source in sources]
    freshness_score = round(mean(freshness_values), 2) if freshness_values else 0.0
    source_types = {source.get("type") for source in sources}
    source_diversity_score = round(min(1.0, len(source_types) / 4), 2) if sources else 0.0
    credibility_values = [source_credibility_score(source) for source in sources]
    provenance_score = round(mean(credibility_values), 2) if credibility_values else 0.0
    age_values = [age for age in (estimate_source_age_days(source) for source in sources) if age is not None]
    average_source_age_days = round(mean(age_values), 1) if age_values else None
    convergence = evidence_convergence(sources)
    convergence_score = float(convergence["convergence_score"])

    coverage_score = round(
        min(
            1.0,
            0.18
            + min(0.28, len(sources) * 0.1)
            + min(0.14, len(execution_artifacts) * 0.04)
            + min(0.14, len(decisions) * 0.08)
            + source_diversity_score * 0.08
            + provenance_score * 0.09
            + convergence_score * 0.09,
        ),
        2,
    )
    contradiction_score = round(
        min(
            1.0,
            contradiction_count * 0.18
            + (0.15 if contradiction_severity == "high" else 0.07 if contradiction_severity == "medium" else 0.0),
        ),
        2,
    )

    evidence_gaps: list[str] = []
    if len(sources) < 3:
        evidence_gaps.append("thesis is supported by fewer than three source artifacts")
    if len(source_types) <= 1:
        evidence_gaps.append("source bundle lacks cross-type evidence diversity")
    if provenance_score < 0.7:
        evidence_gaps.append("source provenance quality is too weak for a durable strategic commitment")
    if convergence_score < 0.45:
        evidence_gaps.append("sources do not yet converge on a coherent wedge strongly enough to justify commitment")
    if not decisions:
        evidence_gaps.append("no committed decision memo anchors the thesis")
    if len(execution_artifacts) < 3:
        evidence_gaps.append("execution surface is thin relative to strategic commitment")
    if freshness_score < 0.7:
        evidence_gaps.append("supporting evidence is aging and should be refreshed")

    hard_triggers: list[str] = []
    if contradiction_severity == "high":
        hard_triggers.append("contradiction load is high enough to force a decision revisit")
    if freshness_score < 0.55:
        hard_triggers.append("core evidence bundle is stale")
    if provenance_score < 0.55:
        hard_triggers.append("core sources are too weakly attributable to sustain a confident thesis")
    if convergence_score < 0.3 and len(sources) >= 3:
        hard_triggers.append("source bundle is broad but still fails to converge on the same wedge")

    soft_triggers: list[str] = []
    if len(source_types) <= 2:
        soft_triggers.append("source diversity is narrow for a product-direction commitment")
    if convergence_score < 0.6:
        soft_triggers.append(convergence["convergence_summary"])
    if len(execution_artifacts) < 4:
        soft_triggers.append("execution artifacts are present but not yet deep enough for confident acceleration")
    if thesis_payload.get("whitespace", {}).get("category_pressure") == "rising":
        soft_triggers.append("category pressure is rising and may compress the wedge")
    if average_source_age_days is not None and average_source_age_days >= 30:
        soft_triggers.append("the average source age is drifting beyond a comfortable review window")

    bundle_health = "strong"
    if freshness_score < 0.5 or contradiction_score >= 0.65 or provenance_score < 0.5 or convergence_score < 0.28:
        bundle_health = "expired"
    elif (
        freshness_score < 0.65
        or contradiction_score >= 0.45
        or provenance_score < 0.62
        or convergence_score < 0.42
        or len(evidence_gaps) >= 3
    ):
        bundle_health = "fragile"
    elif (
        freshness_score < 0.8
        or contradiction_score >= 0.25
        or provenance_score < 0.75
        or convergence_score < 0.62
        or evidence_gaps
    ):
        bundle_health = "watch"

    if bundle_health == "strong":
        recommended_action = "maintain_commitment"
    elif bundle_health == "watch":
        recommended_action = "revisit_soon"
    elif bundle_health == "fragile":
        recommended_action = "refresh_evidence"
    else:
        recommended_action = "rebuild_case"

    source_checks = []
    for source in sources:
        freshness_value = round(float(source.get("freshness_score", 0.0) or 0.0), 2)
        age_days = estimate_source_age_days(source)
        source_checks.append(
            {
                "source_id": source.get("id"),
                "source_type": source.get("type"),
                "freshness": classify_source_freshness(freshness_value),
                "freshness_score": freshness_value,
                "days_since_capture": age_days,
                "provenance_quality": infer_provenance_quality(source),
                "credibility_score": source_credibility_score(source),
                "signals": source.get("signals", [])[:4],
                "support_features": sorted(_source_support_features(source))[:6],
            }
        )

    return {
        "target_id": thesis_payload.get("id"),
        "bundle_health": bundle_health,
        "freshness_score": freshness_score,
        "provenance_score": provenance_score,
        "source_diversity_score": source_diversity_score,
        "average_source_age_days": average_source_age_days,
        "convergence_score": convergence_score,
        "convergence_state": convergence["convergence_state"],
        "average_pairwise_overlap": convergence["average_pairwise_overlap"],
        "shared_support_features": convergence["shared_support_features"],
        "cross_type_support_features": convergence["cross_type_support_features"],
        "convergence_summary": convergence["convergence_summary"],
        "contradiction_score": contradiction_score,
        "coverage_score": coverage_score,
        "source_checks": source_checks,
        "evidence_gaps": evidence_gaps,
        "hard_triggers": hard_triggers,
        "soft_triggers": soft_triggers,
        "recommended_action": recommended_action,
        "review_after": schedule_review_after(bundle_health, freshness_score, contradiction_score, average_source_age_days),
        "decision_ids": [decision.get("id") for decision in decisions],
        "execution_artifact_ids": [artifact.get("id") for artifact in execution_artifacts],
    }


def classify_portfolio_lane(thesis_payload: dict, audit_payload: dict, execution_artifacts: list[dict]) -> tuple[str, str, str]:
    whitespace_score = float(thesis_payload.get("whitespace", {}).get("whitespace_score", 0.0) or 0.0)
    leverage = float(thesis_payload.get("opportunity", {}).get("scores", {}).get("strategic_leverage", 0.0) or 0.0)
    contradiction_count = int(thesis_payload.get("contradictions", {}).get("contradiction_count", 0) or 0)
    decision_states = {decision.get("decision") for decision in audit_payload.get("decision_records", [])}
    bundle_health = audit_payload.get("bundle_health", "watch")
    execution_depth = len(execution_artifacts)

    if bundle_health == "strong" and whitespace_score >= 8.0 and leverage >= 7.8 and execution_depth >= 4:
        return "flagship", "+expand", "high leverage, healthy evidence, and compounding execution surface"
    if contradiction_count >= 3 and bundle_health in {"fragile", "expired"}:
        return "decommission", "-decrease", "contradictions overwhelm the current evidence case"
    if bundle_health in {"fragile", "expired"}:
        return "watchtower", "+stabilize", "direction remains interesting but the evidence bundle is not yet trustworthy"
    if decision_states & {"combine"}:
        return "merge-candidate", "+merge", "decision history already points toward a combined direction"
    if execution_depth <= 2:
        return "incubation", "+prove", "strategic case exists but execution follow-through remains shallow"
    return "watchtower", "+monitor", "keep the thesis active but under disciplined review"


def build_portfolio_review(
    theses: list[dict],
    audits: dict[str, dict],
    decisions_by_thesis: dict[str, list[dict]],
    execution_by_thesis: dict[str, list[dict]],
) -> dict:
    theme_intelligence = build_theme_intelligence(theses)
    merge_opportunities = theme_intelligence.get("merge_candidates", [])
    lane_assignments: list[dict] = []
    drift_alerts: list[dict] = []
    execution_gaps: list[dict] = []
    actions: list[dict] = []

    for thesis_payload in theses:
        thesis_id = thesis_payload["id"]
        audit_payload = audits[thesis_id]
        execution_artifacts = execution_by_thesis.get(thesis_id, [])
        decision_records = decisions_by_thesis.get(thesis_id, [])
        enriched_audit = {**audit_payload, "decision_records": decision_records}
        lane, attention_delta, reason = classify_portfolio_lane(thesis_payload, enriched_audit, execution_artifacts)
        whitespace_score = float(thesis_payload.get("whitespace", {}).get("whitespace_score", 0.0) or 0.0)
        contradiction_score = float(audit_payload.get("contradiction_score", 0.0) or 0.0)
        freshness_score = float(audit_payload.get("freshness_score", 0.0) or 0.0)
        leverage = float(thesis_payload.get("opportunity", {}).get("scores", {}).get("strategic_leverage", 0.0) or 0.0)
        theme_overlap = max(
            [
                item.get("overlap_ratio", 0.0)
                for item in merge_opportunities
                if thesis_id in item.get("pair", [])
            ]
            or [0.0]
        )
        conviction_score = round(
            min(9.8, whitespace_score * 0.45 + leverage * 0.4 + freshness_score * 1.5 - contradiction_score * 1.5 + theme_overlap * 0.35),
            2,
        )
        confidence_score = round(
            max(0.0, min(0.98, audit_payload.get("coverage_score", 0.0) * 0.55 + freshness_score * 0.35 - contradiction_score * 0.25)),
            2,
        )
        lane_assignments.append(
            {
                "thesis_id": thesis_id,
                "name": thesis_payload.get("name"),
                "lane": lane,
                "conviction_score": conviction_score,
                "confidence_score": confidence_score,
                "attention_delta": attention_delta,
                "reason": reason,
                "theme_overlap": round(theme_overlap, 2),
            }
        )

        if audit_payload.get("bundle_health") in {"fragile", "expired"}:
            drift_alerts.append(
                {
                    "thesis_id": thesis_id,
                    "drift_type": "evidence_drift",
                    "severity": "high" if audit_payload.get("bundle_health") == "expired" else "medium",
                    "signal": "; ".join(audit_payload.get("evidence_gaps", [])[:2]) or "evidence bundle weakened",
                    "recommended_action": audit_payload.get("recommended_action"),
                }
            )
        elif float(thesis_payload.get("comparison", {}).get("overlap_strength", 0.0) or 0.0) >= 0.5:
            drift_alerts.append(
                {
                    "thesis_id": thesis_id,
                    "drift_type": "market_drift",
                    "severity": "medium",
                    "signal": "category overlap is increasing relative to thesis differentiation",
                    "recommended_action": "tighten wedge",
                }
            )

        if len(execution_artifacts) < 4:
            execution_gaps.append(
                {
                    "thesis_id": thesis_id,
                    "gap": "execution surface is missing depth across brief, issue tree, roadmap, and review artifacts",
                }
            )

        if lane == "flagship":
            actions.append({"action": "protect_focus", "target_id": thesis_id})
        elif lane == "incubation":
            actions.append({"action": "deepen_execution", "target_id": thesis_id})
        elif lane == "watchtower":
            actions.append({"action": "revisit", "target_id": thesis_id})
        elif lane == "merge-candidate":
            actions.append({"action": "merge", "target_id": thesis_id})
        else:
            actions.append({"action": "decommission", "target_id": thesis_id})

    if theme_intelligence.get("concentration_state") in {"tilted", "concentrated"}:
        for risk in theme_intelligence.get("concentration_risks", []):
            drift_alerts.append(
                {
                    "thesis_id": "portfolio",
                    "drift_type": "portfolio_drift",
                    "severity": "high" if theme_intelligence.get("concentration_state") == "concentrated" else "medium",
                    "signal": f"theme {risk['theme']} spans {risk['thesis_count']} theses and is crowding portfolio variety",
                    "recommended_action": "diversify",
                }
            )

    for overlap in merge_opportunities:
        drift_alerts.append(
            {
                "thesis_id": "+".join(overlap.get("pair", [])),
                "drift_type": "portfolio_overlap",
                "severity": "medium",
                "signal": f"shared themes {', '.join(overlap.get('shared_themes', [])[:3]) or 'none'} create merge uplift {overlap.get('merge_uplift')}",
                "recommended_action": "merge",
            }
        )
        actions.append(
            {
                "action": "evaluate_merge_pair",
                "target_id": "+".join(overlap.get("pair", [])),
                "pair": overlap.get("pair", []),
            }
        )

    lane_counts = Counter(item["lane"] for item in lane_assignments)
    summary = {
        "thesis_count": len(theses),
        "flagship_count": lane_counts.get("flagship", 0),
        "incubation_count": lane_counts.get("incubation", 0),
        "watchtower_count": lane_counts.get("watchtower", 0),
        "merge_candidate_count": lane_counts.get("merge-candidate", 0),
        "decommission_count": lane_counts.get("decommission", 0),
        "concentration_state": theme_intelligence.get("concentration_state"),
        "merge_opportunity_count": len(merge_opportunities),
    }
    return {
        "summary": summary,
        "lane_assignments": sorted(lane_assignments, key=lambda item: (-item["conviction_score"], item["thesis_id"])),
        "drift_alerts": drift_alerts,
        "execution_gaps": execution_gaps,
        "actions": actions,
        "theme_intelligence": theme_intelligence,
        "merge_opportunities": merge_opportunities,
        "diversification_targets": theme_intelligence.get("diversification_targets", []),
    }


def build_portfolio_rebalance(review_payload: dict) -> dict:
    lane_assignments = review_payload.get("lane_assignments", [])
    ordered = sorted(lane_assignments, key=lambda item: (-item.get("conviction_score", 0.0), item.get("thesis_id", "")))
    attention_moves = []
    review_priorities = []
    for item in ordered:
        lane = item.get("lane")
        if lane == "flagship":
            motion = "increase"
        elif lane == "incubation":
            motion = "selective_increase"
        elif lane == "watchtower":
            motion = "hold"
        elif lane == "merge-candidate":
            motion = "compress"
        else:
            motion = "decrease"
        attention_moves.append(
            {
                "thesis_id": item.get("thesis_id"),
                "name": item.get("name"),
                "current_lane": lane,
                "attention_shift": motion,
                "reason": item.get("reason"),
            }
        )
        if lane in {"watchtower", "merge-candidate", "decommission"}:
            review_priorities.append(item.get("thesis_id"))

    theme_intelligence = review_payload.get("theme_intelligence", {})
    concentration_moves = []
    if theme_intelligence.get("concentration_state") in {"tilted", "concentrated"}:
        for risk in theme_intelligence.get("concentration_risks", []):
            concentration_moves.append(
                {
                    "theme": risk.get("theme"),
                    "motion": "diversify",
                    "reason": f"theme share {risk.get('share')} across {risk.get('thesis_count')} theses is compressing portfolio variety",
                }
            )

    return {
        "attention_moves": attention_moves,
        "priority_order": [item.get("thesis_id") for item in ordered],
        "review_priorities": review_priorities,
        "merge_suggestions": [
            {
                "pair": pair.get("pair"),
                "shared_themes": pair.get("shared_themes"),
                "merge_uplift": pair.get("merge_uplift"),
            }
            for pair in review_payload.get("merge_opportunities", [])
        ]
        or [item.get("thesis_id") for item in ordered if item.get("lane") == "merge-candidate"],
        "decommission_candidates": [item.get("thesis_id") for item in ordered if item.get("lane") == "decommission"],
        "concentration_moves": concentration_moves,
        "diversification_targets": review_payload.get("diversification_targets", []),
    }


def _themes_for_thesis(thesis_payload: dict) -> list[str]:
    comparison = thesis_payload.get("comparison", {})
    domain_cues = comparison.get("domain_cues", []) or []
    capability_hints = comparison.get("capability_hints", []) or []
    return sorted(set((domain_cues + capability_hints)[:8]))


def build_theme_intelligence(theses: list[dict]) -> dict:
    theme_counts: dict[str, int] = {}
    thesis_themes: list[dict[str, object]] = []
    for thesis_payload in theses:
        themes = _themes_for_thesis(thesis_payload)
        for theme in themes:
            theme_counts[theme] = theme_counts.get(theme, 0) + 1
        thesis_themes.append(
            {
                "thesis_id": thesis_payload["id"],
                "name": thesis_payload.get("name"),
                "themes": themes,
            }
        )

    dominant = sorted(theme_counts.items(), key=lambda item: (-item[1], item[0]))[:8]
    theme_concentration = round((dominant[0][1] / max(1, len(theses))) if dominant else 0.0, 2)
    total_assignments = sum(theme_counts.values())
    theme_hhi = round(sum((count / total_assignments) ** 2 for count in theme_counts.values()), 3) if total_assignments else 0.0
    if theme_concentration >= 0.65 or theme_hhi >= 0.22:
        concentration_state = "concentrated"
    elif theme_concentration >= 0.45 or theme_hhi >= 0.16:
        concentration_state = "tilted"
    else:
        concentration_state = "balanced"

    cluster_map: dict[str, dict[str, object]] = {}
    for thesis in thesis_themes:
        themes = thesis["themes"]
        if not themes:
            anchor = "unclassified"
        else:
            anchor = sorted(themes, key=lambda theme: (-theme_counts.get(theme, 0), theme))[0]
        cluster = cluster_map.setdefault(
            anchor,
            {
                "cluster_theme": anchor,
                "thesis_ids": [],
                "thesis_names": [],
                "shared_themes": set(),
            },
        )
        cluster["thesis_ids"].append(thesis["thesis_id"])
        cluster["thesis_names"].append(thesis["name"])
        cluster["shared_themes"].update(themes)

    clusters = sorted(
        [
            {
                "cluster_theme": cluster["cluster_theme"],
                "cluster_size": len(cluster["thesis_ids"]),
                "thesis_ids": cluster["thesis_ids"],
                "thesis_names": cluster["thesis_names"],
                "shared_themes": sorted(cluster["shared_themes"]),
            }
            for cluster in cluster_map.values()
        ],
        key=lambda item: (-item["cluster_size"], item["cluster_theme"]),
    )

    concentration_risks = [
        {
            "theme": theme,
            "thesis_count": count,
            "share": round(count / max(1, len(theses)), 2),
        }
        for theme, count in dominant
        if count >= max(2, (len(theses) + 1) // 2)
    ]
    whitespace_themes = sorted(theme for theme, count in theme_counts.items() if count == 1)

    cluster_by_thesis = {
        thesis_id: cluster["cluster_theme"]
        for cluster in clusters
        for thesis_id in cluster["thesis_ids"]
    }
    pairwise_overlaps = []
    bridge_theme_counts: dict[str, set[str]] = {}
    for left, right in combinations(thesis_themes, 2):
        left_themes = set(left["themes"])
        right_themes = set(right["themes"])
        shared_themes = sorted(left_themes & right_themes)
        all_themes = sorted(left_themes | right_themes)
        overlap_ratio = round(len(shared_themes) / max(1, len(all_themes)), 2)
        whitespace_coverage = len({theme for theme in all_themes if theme_counts.get(theme, 0) == 1})
        merge_uplift = round(min(0.98, overlap_ratio * 0.7 + whitespace_coverage * 0.08), 2)
        relationship = "orthogonal"
        if overlap_ratio >= 0.5:
            relationship = "redundant"
        elif shared_themes and whitespace_coverage >= 2:
            relationship = "adjacent"
        elif shared_themes:
            relationship = "related"

        if shared_themes and cluster_by_thesis.get(left["thesis_id"]) != cluster_by_thesis.get(right["thesis_id"]):
            for theme in shared_themes:
                bridge_theme_counts.setdefault(theme, set()).update(
                    {cluster_by_thesis.get(left["thesis_id"], "unclassified"), cluster_by_thesis.get(right["thesis_id"], "unclassified")}
                )

        pairwise_overlaps.append(
            {
                "pair": [left["thesis_id"], right["thesis_id"]],
                "names": [left.get("name"), right.get("name")],
                "shared_themes": shared_themes,
                "overlap_ratio": overlap_ratio,
                "unique_theme_count": len([theme for theme in all_themes if theme not in shared_themes]),
                "merge_uplift": merge_uplift,
                "relationship": relationship,
            }
        )

    pairwise_overlaps = sorted(
        pairwise_overlaps,
        key=lambda item: (-item["merge_uplift"], -item["overlap_ratio"], item["pair"]),
    )
    merge_candidates = [
        overlap
        for overlap in pairwise_overlaps
        if overlap["shared_themes"] and overlap["merge_uplift"] >= 0.4 and overlap["relationship"] in {"redundant", "adjacent"}
    ][:5]
    bridge_themes = [
        {
            "theme": theme,
            "cluster_count": len(cluster_names),
            "clusters": sorted(cluster_names),
        }
        for theme, cluster_names in sorted(bridge_theme_counts.items(), key=lambda item: (-len(item[1]), item[0]))
    ]
    diversification_targets = [
        {
            "theme": theme,
            "thesis_id": thesis["thesis_id"],
            "name": thesis.get("name"),
            "reason": f"{theme} appears in only one thesis and can diversify a {concentration_state} portfolio",
        }
        for theme in whitespace_themes
        for thesis in thesis_themes
        if theme in thesis["themes"]
    ]

    return {
        "dominant_themes": [{"theme": theme, "count": count} for theme, count in dominant],
        "theme_concentration": theme_concentration,
        "theme_hhi": theme_hhi,
        "concentration_state": concentration_state,
        "thesis_themes": thesis_themes,
        "clusters": clusters,
        "concentration_risks": concentration_risks,
        "whitespace_themes": whitespace_themes,
        "pairwise_overlaps": pairwise_overlaps,
        "merge_candidates": merge_candidates,
        "bridge_themes": bridge_themes,
        "diversification_targets": diversification_targets,
    }
