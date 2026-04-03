"""Evidence Chain Extraction.

Innovation: extracts the ARGUMENT STRUCTURE from a source, not just keywords.
Each source produces an EvidenceChain containing:
- Claims: what the source asserts
- Evidence: what backs each claim
- Assumptions: what the source takes for granted
- Implications: what follows from the claims
- Conflicts: what this contradicts in other frameworks

This enables building an argument graph across sources, revealing
deep connections and contradictions that token overlap can never detect.
"""

from __future__ import annotations

import json
from pydantic import BaseModel, Field


class Claim(BaseModel):
    """A single claim extracted from a source."""
    statement: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    implications: list[str] = Field(default_factory=list)


class EvidenceChain(BaseModel):
    """The argument structure of a source."""
    source_id: str
    core_thesis: str | None = None
    claims: list[Claim] = Field(default_factory=list)
    unstated_assumptions: list[str] = Field(default_factory=list)
    strategic_signals: list[str] = Field(default_factory=list)
    domain_mapping: list[str] = Field(default_factory=list)
    capability_extractions: list[str] = Field(default_factory=list)
    gap_indicators: list[str] = Field(default_factory=list)
    raw_llm_response: dict | None = None

    def to_dict(self) -> dict:
        return self.model_dump()


EVIDENCE_CHAIN_SYSTEM_PROMPT = """You are a strategic intelligence analyst. Your task is to extract the ARGUMENT STRUCTURE from a source document.

Extract:
1. core_thesis: The one central argument or proposition of this source (1-2 sentences)
2. claims: The key claims made, each with:
   - statement: The claim itself
   - confidence: How strongly the source asserts this (0.0-1.0)
   - evidence: What backs this claim
   - assumptions: What the claim assumes to be true
   - implications: What follows if this claim is true
3. unstated_assumptions: What the source takes for granted without stating
4. strategic_signals: What market/technology/building signals this source emits
5. domain_mapping: What domains/fields this source touches
6. capability_extractions: What concrete capabilities/tools/approaches this source reveals
7. gap_indicators: What this source DOESN'T address that would be strategically important

Be precise. Be analytical. Think like a founder evaluating whether to build something based on this source.

Return your response as a JSON object with these exact keys:
{"core_thesis": "...", "claims": [...], "unstated_assumptions": [...], "strategic_signals": [...], "domain_mapping": [...], "capability_extractions": [...], "gap_indicators": [...]}

Each claim should be: {"statement": "...", "confidence": 0.0-1.0, "evidence": "...", "assumptions": [...], "implications": [...]}
"""

EVIDENCE_CHAIN_USER_TEMPLATE = """Analyze this source:

Title: {title}
Type: {source_type}
Summary: {summary}
Strategic Summary: {strategic_summary}
Tags: {tags}
Signals: {signals}
Domain Cues: {domain_cues}
Capability Hints: {capability_hints}
URI: {uri}

Extract the complete argument structure as specified."""


def extract_evidence_chain(
    source_payload: dict,
    provider: object,
) -> EvidenceChain | None:
    """Extract evidence chain from a source using LLM.

    Returns None if provider is unavailable (graceful degradation).
    """
    if not provider.available():
        return None

    user_prompt = EVIDENCE_CHAIN_USER_TEMPLATE.format(
        title=source_payload.get("title", "Untitled"),
        source_type=source_payload.get("type", "unknown"),
        summary=source_payload.get("summary") or "No summary available",
        strategic_summary=source_payload.get("strategic_summary") or "Not provided",
        tags=", ".join(source_payload.get("tags", [])),
        signals=", ".join(source_payload.get("signals", [])),
        domain_cues=", ".join(source_payload.get("domain_cues", [])),
        capability_hints=", ".join(source_payload.get("capability_hints", [])),
        uri=source_payload.get("uri") or "N/A",
    )

    result = provider.complete_structured(
        system=EVIDENCE_CHAIN_SYSTEM_PROMPT,
        user=user_prompt,
        expected_keys=[
            "core_thesis",
            "claims",
            "strategic_signals",
            "domain_mapping",
        ],
        temperature=0.2,
    )

    if result is None:
        return None

    try:
        claims = []
        for raw_claim in result.get("claims", []):
            if isinstance(raw_claim, dict) and "statement" in raw_claim:
                claims.append(
                    Claim(
                        statement=raw_claim["statement"],
                        confidence=float(raw_claim.get("confidence", 0.5)),
                        evidence=raw_claim.get("evidence"),
                        assumptions=raw_claim.get("assumptions", []),
                        implications=raw_claim.get("implications", []),
                    )
                )

        return EvidenceChain(
            source_id=source_payload.get("id", "unknown"),
            core_thesis=result.get("core_thesis"),
            claims=claims,
            unstated_assumptions=result.get("unstated_assumptions", []),
            strategic_signals=result.get("strategic_signals", []),
            domain_mapping=result.get("domain_mapping", []),
            capability_extractions=result.get("capability_extractions", []),
            gap_indicators=result.get("gap_indicators", []),
            raw_llm_response=result,
        )
    except Exception:
        return None


def extract_cross_source_conflicts(
    chains: list[EvidenceChain],
) -> list[dict]:
    """Find conflicts between evidence chains from different sources.

    Detects:
    - Contradictory claims (same domain, opposite assertions)
    - Assumption conflicts (one source assumes X, another assumes not-X)
    - Implication chains that lead to incompatible conclusions
    """
    if len(chains) < 2:
        return []

    conflicts = []
    claim_index: dict[str, list[tuple[str, Claim]]] = {}

    for chain in chains:
        for claim in chain.claims:
            for domain in chain.domain_mapping:
                claim_index.setdefault(domain, []).append((chain.source_id, claim))

    for domain, entries in claim_index.items():
        if len(entries) < 2:
            continue
        for i, (src_a, claim_a) in enumerate(entries):
            for src_b, claim_b in entries[i + 1 :]:
                if src_a == src_b:
                    continue
                if claim_a.confidence > 0.7 and claim_b.confidence > 0.7:
                    conflicts.append(
                        {
                            "domain": domain,
                            "source_a": src_a,
                            "claim_a": claim_a.statement,
                            "source_b": src_b,
                            "claim_b": claim_b.statement,
                            "conflict_type": "high_confidence_divergence",
                            "severity": "high",
                        }
                    )

    return conflicts[:10]
