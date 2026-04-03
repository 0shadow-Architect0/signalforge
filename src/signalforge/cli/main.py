from __future__ import annotations

from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import hashlib
import json
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import typer

from signalforge import __version__
from signalforge.analysis import (
    audit_evidence_bundle,
    build_portfolio_rebalance,
    build_portfolio_review,
    build_theme_intelligence,
    compare_sources,
    extract_contradictions,
    score_opportunity,
    whitespace_from_comparison,
)
from signalforge.artifacts import write_artifact
from signalforge.models import DecisionMemo, InsightMemo, OpportunityEvaluation, Source, Thesis
from signalforge.workspace import build_workspace, slugify, utc_now
from signalforge.semantic.config import SemanticConfig
from signalforge.semantic.provider import create_provider
from signalforge.semantic.enricher import (
    enrich_source as semantic_enrich_source,
    enrich_comparison as semantic_enrich_comparison,
    enrich_contradictions as semantic_enrich_contradictions,
    enrich_whitespace as semantic_enrich_whitespace,
    calibrate_confidence,
)
from signalforge.semantic.evidence import extract_evidence_chain

app = typer.Typer(help="SignalForge CLI", no_args_is_help=True)
workspace_app = typer.Typer(help="Manage local strategic workspaces")
intake_app = typer.Typer(help="Ingest source material")
analyze_app = typer.Typer(help="Generate strategic analysis artifacts")
thesis_app = typer.Typer(help="Generate product theses")
decide_app = typer.Typer(help="Commit explicit strategic decisions")
evidence_app = typer.Typer(help="Audit evidence vitality and strategic trust")
portfolio_app = typer.Typer(help="Portfolio-level operations")
execution_app = typer.Typer(help="Convert strategic decisions into build artifacts")
export_app = typer.Typer(help="Generate public-facing surfaces from internal artifacts")

app.add_typer(workspace_app, name="workspace")
app.add_typer(intake_app, name="intake")
app.add_typer(analyze_app, name="analyze")
app.add_typer(thesis_app, name="thesis")
app.add_typer(decide_app, name="decide")
app.add_typer(evidence_app, name="evidence")
app.add_typer(portfolio_app, name="portfolio")
app.add_typer(execution_app, name="execution")
app.add_typer(export_app, name="export")
semantic_app = typer.Typer(help="Semantic intelligence layer (LLM-powered)")
app.add_typer(semantic_app, name="semantic")


def default_root() -> Path:
    return Path.cwd() / ".signalforge"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def get_workspace(name: str, root: Path) -> tuple[Path, object]:
    workspace = build_workspace(name=name, root=root)
    return workspace.workspace_dir, workspace


def load_artifact_json(root: Path, workspace_name: str, artifact_type: str, artifact_id: str) -> dict:
    workspace = build_workspace(name=workspace_name, root=root)
    path = workspace.artifact_dir(artifact_type) / f"{artifact_id}.json"
    if not path.exists():
        raise typer.BadParameter(f"Artifact not found: {artifact_type}/{artifact_id}")
    return load_json(path)


def artifact_exists(root: Path, workspace_name: str, artifact_type: str, artifact_id: str) -> bool:
    workspace = build_workspace(name=workspace_name, root=root)
    path = workspace.artifact_dir(artifact_type) / f"{artifact_id}.json"
    return path.exists()


def load_artifact_collection(workspace, artifact_type: str) -> list[dict]:
    return [load_json(path) for path in sorted(workspace.artifact_dir(artifact_type).glob("*.json"))]


def execution_artifacts_for_thesis(workspace, thesis_id: str) -> list[dict]:
    return [
        payload
        for payload in load_artifact_collection(workspace, "experiment")
        if payload.get("thesis_id") == thesis_id
    ]


def decision_artifacts_for_thesis(workspace, thesis_id: str) -> list[dict]:
    return [
        payload
        for payload in load_artifact_collection(workspace, "decision")
        if payload.get("thesis_id") == thesis_id
    ]


def evidence_audit_payload(root: Path, workspace_name: str, thesis_payload: dict) -> dict:
    workspace = build_workspace(name=workspace_name, root=root)
    source_ids = thesis_payload.get("source_ids", [])
    sources = [load_artifact_json(root, workspace_name, "source", source_id) for source_id in source_ids]
    decisions = decision_artifacts_for_thesis(workspace, thesis_payload["id"])
    execution_artifacts = execution_artifacts_for_thesis(workspace, thesis_payload["id"])
    return audit_evidence_bundle(thesis_payload, sources, decisions, execution_artifacts)


def compute_decision_intelligence(thesis_payload: dict) -> dict:
    comparison = thesis_payload.get("comparison", {})
    contradictions = thesis_payload.get("contradictions", {})
    whitespace = thesis_payload.get("whitespace", {})
    shared = comparison.get("shared_capabilities", [])
    diff = comparison.get("differentiation_zones", [])
    overlap_strength = float(comparison.get("overlap_strength", 0.0) or 0.0)
    contradiction_count = int(contradictions.get("contradiction_count", 0) or 0)
    evidence_density = round(min(1.0, (len(shared) + len(diff)) / 10), 2)
    contradiction_load = round(min(1.0, max(0.0, overlap_strength - (len(diff) * 0.08)) + contradiction_count * 0.08), 2)
    confidence_before = round(min(0.95, 0.45 + evidence_density * 0.25), 2)
    confidence_after = round(min(0.98, confidence_before + 0.12 + len(shared) * 0.03 + len(diff) * 0.02 - contradiction_load * 0.08), 2)
    return {
        "evidence_density": evidence_density,
        "contradiction_load": contradiction_load,
        "contradiction_count": contradiction_count,
        "contradiction_severity": contradictions.get("severity"),
        "confidence_before": confidence_before,
        "confidence_after": confidence_after,
        "whitespace_score": whitespace.get("whitespace_score"),
        "category_pressure": whitespace.get("category_pressure"),
    }


def source_fingerprint(input_value: str, source_type: str, title: str) -> str:
    digest = hashlib.sha256(f"{source_type}|{title}|{input_value}".encode("utf-8")).hexdigest()
    return f"sha256:{digest[:16]}"


def source_author(input_value: str) -> str | None:
    if "github.com/" in input_value:
        parts = [part for part in input_value.split("/") if part]
        try:
            idx = parts.index("github.com")
            return parts[idx + 1]
        except Exception:
            return None
    return None


def source_tags(source_type: str, title: str, summary: str | None) -> list[str]:
    tags = {source_type, slugify(title)}
    text = f"{title} {summary or ''}".lower()
    for token in ["agent", "research", "workflow", "decision", "graph", "builder", "orchestration", "paper", "repo"]:
        if token in text:
            tags.add(token)
    return sorted(tags)


def source_signals(source_type: str, title: str, summary: str | None) -> list[str]:
    text = f"{title} {summary or ''}".lower()
    signals = []
    if "agent" in text:
        signals.append("agent-native")
    if "research" in text:
        signals.append("research-intense")
    if "decision" in text or "strategy" in text:
        signals.append("decision-grade")
    if "workflow" in text or "orchestration" in text:
        signals.append("workflow-system")
    if not signals:
        signals.append(f"{source_type}-signal")
    return signals


def strategic_summary_for_source(source_type: str, title: str, summary: str | None) -> str:
    return (
        f"{title} contributes {source_type}-grade evidence that may reveal reusable primitives, category pressure, and wedge opportunities "
        f"when combined with adjacent signals."
    )


def infer_domain_cues(source_type: str, title: str, summary: str | None, metadata: dict[str, str]) -> list[str]:
    text = f"{title} {summary or ''} {' '.join(metadata.values())}".lower()
    cues = []
    for token in ["agent", "research", "workflow", "graph", "memory", "orchestration", "builder", "paper", "market"]:
        if token in text:
            cues.append(token)
    if source_type == "paper":
        cues.append("research-literature")
    if source_type == "article":
        cues.append("market-framing")
    if source_type == "repo":
        cues.append("implementation-surface")
    return sorted(set(cues))


def infer_capability_hints(source_type: str, title: str, summary: str | None, metadata: dict[str, str]) -> list[str]:
    text = f"{title} {summary or ''} {' '.join(metadata.values())}".lower()
    hints = []
    mapping = {
        "agent": "agent-coordination",
        "research": "research-automation",
        "workflow": "workflow-orchestration",
        "graph": "graph-structured-reasoning",
        "memory": "memory-layer",
        "orchestration": "system-orchestration",
        "paper": "literature-ingestion",
        "builder": "builder-tooling",
    }
    for token, hint in mapping.items():
        if token in text:
            hints.append(hint)
    if not hints:
        hints.append(f"{source_type}-analysis")
    return sorted(set(hints))


def _parse_metadata_datetime(raw: str | None) -> datetime | None:
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


def infer_freshness_score(source_type: str, metadata: dict[str, str]) -> float:
    now = datetime.now(timezone.utc)
    base_scores = {
        "repo": 0.9,
        "paper": 0.82 if metadata.get("paper_source") == "arxiv" else 0.76,
        "article": 0.72 if metadata.get("hostname") else 0.64,
        "note": 0.58,
        "market": 0.68,
    }
    base = base_scores.get(source_type, 0.6)
    parsed = _parse_metadata_datetime(
        metadata.get("updated_at") or metadata.get("published_at") or metadata.get("last_modified")
    )
    if parsed is None:
        return round(base, 2)
    age_days = max(0, int((now - parsed).total_seconds() // 86400))
    if age_days <= 3:
        freshness = min(0.98, base + 0.06)
    elif age_days <= 14:
        freshness = min(0.95, base + 0.02)
    elif age_days <= 45:
        freshness = base
    elif age_days <= 120:
        freshness = max(0.52, base - 0.12)
    else:
        freshness = max(0.4, base - 0.22)
    return round(freshness, 2)


def fetch_github_repo_metadata(input_value: str) -> dict[str, str]:
    if "github.com/" not in input_value:
        return {}
    parts = [part for part in input_value.split("/") if part]
    try:
        idx = parts.index("github.com")
        owner = parts[idx + 1]
        repo = parts[idx + 2]
    except Exception:
        return {}
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    request = urllib.request.Request(api_url, headers={"User-Agent": "SignalForge"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return {}
    return {
        "github_owner": owner,
        "github_repo": repo,
        "stars": str(payload.get("stargazers_count", "")),
        "forks": str(payload.get("forks_count", "")),
        "language": str(payload.get("language", "")),
        "repo_description": str(payload.get("description", "")),
        "updated_at": str(payload.get("updated_at", "")),
    }


def fetch_article_metadata(input_value: str) -> dict[str, str]:
    if not input_value.startswith(("http://", "https://")):
        return {}
    parsed = urlparse(input_value)
    metadata = {"hostname": parsed.netloc, "path": parsed.path}
    try:
        request = urllib.request.Request(input_value, headers={"User-Agent": "SignalForge"})
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read(4096).decode("utf-8", "ignore")
        match = re.search(r"<title>(.*?)</title>", raw, re.IGNORECASE | re.DOTALL)
        if match:
            metadata["page_title"] = re.sub(r"\s+", " ", match.group(1)).strip()
        if response.headers.get("Last-Modified"):
            metadata["last_modified"] = response.headers.get("Last-Modified", "")
    except (urllib.error.URLError, TimeoutError):
        pass
    return metadata


def fetch_arxiv_metadata(input_value: str) -> dict[str, str]:
    if "arxiv.org/abs/" not in input_value:
        return {}
    arxiv_id = input_value.rstrip("/").split("/")[-1]
    api_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    try:
        data = urllib.request.urlopen(api_url, timeout=10).read()
        root = ET.fromstring(data)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        entry = root.find("a:entry", ns)
        if entry is None:
            return {}
        title = entry.find("a:title", ns)
        summary = entry.find("a:summary", ns)
        published = entry.find("a:published", ns)
        updated = entry.find("a:updated", ns)
        authors = [node.find("a:name", ns).text for node in entry.findall("a:author", ns) if node.find("a:name", ns) is not None]
        return {
            "paper_id": arxiv_id,
            "paper_title": " ".join(title.text.split()) if title is not None and title.text else "",
            "paper_summary": " ".join(summary.text.split())[:500] if summary is not None and summary.text else "",
            "paper_authors": ", ".join(authors),
            "paper_source": "arxiv",
            "published_at": published.text if published is not None and published.text else "",
            "updated_at": updated.text if updated is not None and updated.text else "",
        }
    except (urllib.error.URLError, TimeoutError, ET.ParseError):
        return {}
    author = source_author(input_value)

def enrich_source(input_value: str, source_type: str, title: str, summary: str | None) -> dict[str, object]:
    metadata = {"captured_from": "url" if input_value.startswith(("http://", "https://")) else "local", "source_type": source_type}
    author = source_author(input_value)
    tags = source_tags(source_type, title, summary)
    signals = source_signals(source_type, title, summary)
    strategic_summary = strategic_summary_for_source(source_type, title, summary)
    if source_type == "repo" and "github.com/" in input_value:
        gh = fetch_github_repo_metadata(input_value)
        if gh:
            metadata.update({k: v for k, v in gh.items() if v})
            if gh.get("language"):
                tags.append(slugify(gh["language"]))
            if gh.get("repo_description"):
                repo_description = gh["repo_description"]
                strategic_summary = (
                    f"{title} is a GitHub-native repo signal in {gh.get('language', 'unknown language')} with {gh.get('stars', '?')} stars. "
                    f"It suggests strategic relevance around: {repo_description}"
                )
                for token in ["agent", "research", "workflow", "graph", "memory", "orchestration"]:
                    if token in repo_description.lower() and token not in tags:
                        tags.append(token)
                if gh.get("stars"):
                    try:
                        stars = int(gh["stars"])
                        if stars >= 10000:
                            signals.append("high-traction")
                    except ValueError:
                        pass
    elif source_type == "article":
        article = fetch_article_metadata(input_value)
        if article:
            metadata.update({k: v for k, v in article.items() if v})
            if article.get("hostname"):
                tags.append(slugify(article["hostname"]))
            signals.append("article-signal")
            strategic_summary = (
                f"{title} is an article signal from {article.get('hostname', 'an external publication')} that may reveal market framing, language patterns, or timing cues."
            )
    elif source_type == "paper":
        paper = fetch_arxiv_metadata(input_value)
        if paper:
            metadata.update({k: v for k, v in paper.items() if v})
            if paper.get("paper_source"):
                tags.append(paper["paper_source"])
            signals.append("paper-signal")
            if paper.get("paper_authors"):
                author = paper["paper_authors"]
            strategic_summary = (
                f"{title} is a paper signal sourced from {paper.get('paper_source', 'a paper archive')} and contributes research-grade evidence around {paper.get('paper_title', title)}."
            )
    metadata = {k: str(v) for k, v in metadata.items() if v is not None and v != ""}
    domain_cues = infer_domain_cues(source_type, title, summary, metadata)
    capability_hints = infer_capability_hints(source_type, title, summary, metadata)
    freshness_score = infer_freshness_score(source_type, metadata)
    return {
        "author": author or metadata.get("github_owner"),
        "tags": sorted(set(filter(None, tags))),
        "signals": sorted(set(filter(None, signals))),
        "domain_cues": domain_cues,
        "capability_hints": capability_hints,
        "freshness_score": freshness_score,
        "strategic_summary": strategic_summary,
        "metadata": metadata,
    }


def _get_semantic_provider() -> object:
    """Create semantic provider from environment configuration.

    Returns NoOpProvider when SF_SEMANTIC_PROVIDER is not set,
    ensuring graceful degradation to deterministic-only mode.
    """
    config = SemanticConfig.from_env()
    return create_provider(config)


@semantic_app.command("status")
def semantic_status() -> None:
    """Show semantic layer configuration status."""
    config = SemanticConfig.from_env()
    provider = create_provider(config)
    if config.enabled:
        typer.echo(f"Semantic Layer: ENABLED")
        typer.echo(f"  Provider: {config.provider}")
        typer.echo(f"  Model: {config.model}")
        typer.echo(f"  Base URL: {config.base_url}")
        typer.echo(f"  Temperature: {config.temperature}")
        typer.echo(f"  Max Tokens: {config.max_tokens}")
    else:
        typer.echo("Semantic Layer: DISABLED (deterministic-only mode)")
        typer.echo("  Set SF_SEMANTIC_PROVIDER=openai and SF_SEMANTIC_API_KEY=<key> to enable")


@semantic_app.command("test")
def semantic_test() -> None:
    """Test semantic layer connectivity."""
    config = SemanticConfig.from_env()
    provider = create_provider(config)
    if not provider.available():
        typer.echo("Semantic layer not configured. Run 'forge semantic status' for details.")
        return
    result = provider.complete(
        system="You are a helpful assistant.",
        user="Reply with exactly: SEMANTIC_OK",
        max_tokens=20,
    )
    if result:
        typer.echo(f"Connection successful: {result}")
    else:
        typer.echo("Connection failed. Check your API key and base URL.")


@app.callback()
def main() -> None:
    """SignalForge command surface root."""


@app.command()
def version() -> None:
    typer.echo(f"SignalForge {__version__}")


@app.command()
def about() -> None:
    typer.echo("SignalForge: artifact-first product direction engine")


@app.command("artifact-types")
def artifact_types() -> None:
    for name in [
        "source",
        "insight-memo",
        "opportunity-evaluation",
        "product-thesis",
        "decision-memo",
        "experiment-pack",
        "portfolio-review",
        "drift-alert",
        "publish-pack",
    ]:
        typer.echo(name)


@app.command("decision-states")
def decision_states() -> None:
    for state in ["active", "build", "incubate", "watch", "combine", "reject", "revisit"]:
        typer.echo(state)


@workspace_app.command("init")
def workspace_init(
    name: str,
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace = build_workspace(name=name, root=root)
    typer.echo(f"Workspace ready: {workspace.workspace_dir}")


@intake_app.command("add")
def intake_add(
    input_value: str,
    type: str = typer.Option("note", "--type"),
    workspace: str = typer.Option("default", "--workspace"),
    title: str | None = typer.Option(None, "--title"),
    summary: str | None = typer.Option(None, "--summary"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace_paths = build_workspace(name=workspace, root=root)
    source_title = title or input_value.rsplit("/", 1)[-1] or input_value
    source_id = f"src_{type}_{slugify(source_title)}"
    resolved_summary = summary or f"Captured {type} signal for strategic evaluation."
    enrichment = enrich_source(input_value, type, source_title, resolved_summary)
    source = Source(
        id=source_id,
        type=type,
        title=source_title,
        uri=input_value if input_value.startswith(("http://", "https://")) else None,
        summary=resolved_summary,
        strategic_summary=str(enrichment["strategic_summary"]),
        fingerprint=source_fingerprint(input_value, type, source_title),
        author=str(enrichment.get("author") or "") or None,
        tags=list(enrichment["tags"]),
        signals=list(enrichment["signals"]),
        domain_cues=list(enrichment["domain_cues"]),
        capability_hints=list(enrichment["capability_hints"]),
        freshness_score=float(enrichment["freshness_score"]),
        metadata=dict(enrichment["metadata"]),
        workspace=workspace,
    )
    body = (
        f"**Type:** {source.type}\n\n"
        f"**Title:** {source.title}\n\n"
        f"**URI:** {source.uri or 'local-note'}\n\n"
        f"**Author:** {source.author or 'unknown'}\n\n"
        f"**Fingerprint:** {source.fingerprint}\n\n"
        f"**Tags:** {', '.join(source.tags)}\n\n"
        f"**Signals:** {', '.join(source.signals)}\n\n"
        f"**Domain Cues:** {', '.join(source.domain_cues)}\n\n"
        f"**Capability Hints:** {', '.join(source.capability_hints)}\n\n"
        f"**Freshness Score:** {source.freshness_score}\n\n"
        f"**Summary:** {source.summary}\n\n"
        f"**Strategic Summary:** {source.strategic_summary}\n"
    )
    write_artifact(
        workspace_paths,
        artifact_type="source",
        artifact_id=source.id,
        markdown_title=source.title,
        markdown_body=body,
        payload={**source.model_dump(mode="json"), "updated_at": utc_now()},
    )
    typer.echo(source.id)


@analyze_app.command("source")
def analyze_source(
    source_id: str,
    workspace: str = typer.Option("default", "--workspace"),
    semantic: bool = typer.Option(False, "--semantic", help="Enable LLM-powered deep enrichment"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace_paths = build_workspace(name=workspace, root=root)
    source_payload = load_artifact_json(root, workspace, "source", source_id)
    source = Source(**source_payload)
    primitives = [source.type, source.title.split()[0].lower() if source.title.split() else source.type, "strategic-signal"]

    # Semantic enrichment: extract evidence chain + deep enrichment
    semantic_data = {}
    if semantic:
        provider = _get_semantic_provider()
        chain = extract_evidence_chain(source_payload, provider)
        if chain:
            semantic_data["evidence_chain"] = chain.to_dict()
        enrichment = semantic_enrich_source(source_payload, provider)
        if enrichment:
            semantic_data["semantic_enrichment"] = enrichment

    insight = InsightMemo(
        id=f"insight_{slugify(source.title)}",
        source_ids=[source.id],
        core_summary=(
            f"{source.title} matters less as isolated content and more as strategic evidence that can be combined "
            f"with adjacent signals to sharpen product direction."
        ),
        reusable_primitives=sorted({slugify(item) for item in primitives}),
        confidence=0.76,
        workspace=workspace,
    )
    body = (
        f"**Core Summary:** {insight.core_summary}\n\n"
        f"**Reusable Primitives:** {', '.join(insight.reusable_primitives)}\n\n"
        f"**Confidence:** {insight.confidence}\n\n"
        f"**Derived From:** {', '.join(insight.source_ids)}\n"
    )
    if semantic_data:
        body += "\n**Semantic Enrichment:**\n"
        if "semantic_enrichment" in semantic_data:
            se = semantic_data["semantic_enrichment"]
            if se.get("semantic_strategic_summary"):
                body += f"- Strategic Summary: {se['semantic_strategic_summary']}\n"
            if se.get("semantic_opportunity_hints"):
                body += f"- Opportunity Hints: {', '.join(se['semantic_opportunity_hints'][:3])}\n"
            if se.get("semantic_risk_indicators"):
                body += f"- Risks: {', '.join(se['semantic_risk_indicators'][:3])}\n"
        if "evidence_chain" in semantic_data:
            chain = semantic_data["evidence_chain"]
            if chain.get("core_thesis"):
                body += f"- Core Thesis: {chain['core_thesis']}\n"
            if chain.get("claims"):
                body += f"- Claims Extracted: {len(chain['claims'])}\n"
    payload = {**insight.model_dump(mode="json"), "updated_at": utc_now(), **semantic_data}
    write_artifact(
        workspace_paths,
        artifact_type="insight",
        artifact_id=insight.id,
        markdown_title=f"Insight from {source.title}",
        markdown_body=body,
        payload=payload,
    )
    typer.echo(insight.id)


@analyze_app.command("compare")
def analyze_compare(
    source_ids: list[str] = typer.Option(..., "--source"),
    workspace: str = typer.Option("default", "--workspace"),
    semantic: bool = typer.Option(False, "--semantic", help="Enable LLM-powered deep synthesis"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace_paths = build_workspace(name=workspace, root=root)
    sources = [Source(**load_artifact_json(root, workspace, "source", source_id)) for source_id in source_ids]
    comparison = compare_sources(sources)
    artifact_id = f"comparison_{slugify('-'.join(source_ids))}"

    # Semantic enrichment
    semantic_data = {}
    if semantic:
        provider = _get_semantic_provider()
        source_dicts = [s.model_dump(mode="json") for s in sources]
        enrichment = semantic_enrich_comparison(source_dicts, comparison, provider)
        if enrichment:
            semantic_data["semantic_synthesis"] = enrichment

    body = (
        f"**Comparison Summary:** {comparison['comparison_summary']}\n\n"
        f"**Source Types:** {', '.join(comparison['source_types'])}\n\n"
        f"**Shared Capabilities:** {', '.join(comparison['shared_capabilities']) or 'none'}\n\n"
        f"**Differentiation Zones:** {', '.join(comparison['differentiation_zones']) or 'none'}\n\n"
        f"**Overlap Strength:** {comparison['overlap_strength']}\n"
    )
    if semantic_data.get("semantic_synthesis"):
        ss = semantic_data["semantic_synthesis"]
        if ss.get("semantic_synthesis_opportunity"):
            body += f"\n**Semantic Synthesis:** {ss['semantic_synthesis_opportunity']}\n"
        if ss.get("semantic_hidden_connections"):
            body += f"\n**Hidden Connections:** {', '.join(ss['semantic_hidden_connections'][:3])}\n"

    payload = {**comparison, "id": artifact_id, "workspace": workspace, "created_at": utc_now(), "updated_at": utc_now(), **semantic_data}
    write_artifact(
        workspace_paths,
        artifact_type="insight",
        artifact_id=artifact_id,
        markdown_title="Comparative Analysis",
        markdown_body=body,
        payload=payload,
    )
    typer.echo(artifact_id)


@analyze_app.command("contradictions")
def analyze_contradictions(
    source_ids: list[str] = typer.Option(..., "--source"),
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace_paths = build_workspace(name=workspace, root=root)
    sources = [Source(**load_artifact_json(root, workspace, "source", source_id)) for source_id in source_ids]
    comparison = compare_sources(sources)
    contradictions = extract_contradictions(sources, comparison)
    artifact_id = f"contradictions_{slugify('-'.join(source_ids))}"
    body = (
        f"**Severity:** {contradictions['severity']}\n\n"
        f"**Contradiction Count:** {contradictions['contradiction_count']}\n\n"
        f"**Contradictions:**\n" + "\n".join(f"- {item}" for item in contradictions['contradictions'] or ['none']) + "\n"
    )
    payload = {**contradictions, "comparison": comparison, "id": artifact_id, "workspace": workspace, "created_at": utc_now(), "updated_at": utc_now()}
    write_artifact(workspace_paths, "insight", artifact_id, "Contradiction Analysis", body, payload)
    typer.echo(artifact_id)


@analyze_app.command("whitespaces")
def analyze_whitespaces(
    source_ids: list[str] = typer.Option(..., "--source"),
    workspace: str = typer.Option("default", "--workspace"),
    title: str | None = typer.Option(None, "--title"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace_paths = build_workspace(name=workspace, root=root)
    sources = [Source(**load_artifact_json(root, workspace, "source", source_id)) for source_id in source_ids]
    comparison = compare_sources(sources)
    whitespace = whitespace_from_comparison(comparison)
    artifact_title = title or f"Whitespace from {' + '.join(source.title for source in sources)}"
    scores = score_opportunity(sources, comparison, whitespace)
    opportunity = OpportunityEvaluation(
        id=f"opp_{slugify(artifact_title)}",
        derived_from=[source.id for source in sources],
        title=artifact_title,
        scores=scores,
        recommended_motion=whitespace["recommended_motion"],
        workspace=workspace,
    )
    body = (
        f"**Wedge Statement:** {whitespace['wedge_statement']}\n\n"
        f"**Category Pressure:** {whitespace['category_pressure']}\n\n"
        f"**Whitespace Score:** {whitespace['whitespace_score']}\n\n"
        f"**Shared Capabilities:** {', '.join(comparison['shared_capabilities']) or 'none'}\n\n"
        f"**Differentiation Zones:** {', '.join(comparison['differentiation_zones']) or 'none'}\n\n"
        f"**Recommended Motion:** {opportunity.recommended_motion}\n\n"
        f"**Scores:**\n"
        f"- novelty: {opportunity.scores.novelty}\n"
        f"- urgency: {opportunity.scores.urgency}\n"
        f"- founder_fit: {opportunity.scores.founder_fit}\n"
        f"- buildability: {opportunity.scores.buildability}\n"
        f"- monetization: {opportunity.scores.monetization}\n"
        f"- strategic_leverage: {opportunity.scores.strategic_leverage}\n"
    )
    payload = {
        **opportunity.model_dump(mode='json'),
        'comparison': comparison,
        'whitespace': whitespace,
        'updated_at': utc_now(),
    }
    write_artifact(
        workspace_paths,
        artifact_type="opportunity",
        artifact_id=opportunity.id,
        markdown_title=opportunity.title,
        markdown_body=body,
        payload=payload,
    )
    typer.echo(opportunity.id)


@thesis_app.command("create")
def thesis_create(
    source_ids: list[str] = typer.Option(..., "--source"),
    title: str = typer.Option(..., "--title"),
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace_paths = build_workspace(name=workspace, root=root)
    sources = [Source(**load_artifact_json(root, workspace, "source", source_id)) for source_id in source_ids]
    comparison = compare_sources(sources)
    contradictions = extract_contradictions(sources, comparison)
    whitespace = whitespace_from_comparison(comparison)
    opportunity = OpportunityEvaluation(
        id=f"opp_{slugify(title)}",
        derived_from=[source.id for source in sources],
        title=title,
        scores=score_opportunity(sources, comparison, whitespace),
        recommended_motion=whitespace["recommended_motion"],
        workspace=workspace,
    )
    opportunity_body = (
        f"**Opportunity Statement:** {whitespace['wedge_statement']}\n\n"
        f"**Category Pressure:** {whitespace['category_pressure']}\n\n"
        f"**Recommended Motion:** {opportunity.recommended_motion}\n\n"
        f"**Shared Capabilities:** {', '.join(comparison['shared_capabilities']) or 'none'}\n\n"
        f"**Differentiation Zones:** {', '.join(comparison['differentiation_zones']) or 'none'}\n\n"
        f"**Contradiction Severity:** {contradictions['severity']}\n\n"
        f"**Scores:**\n"
        f"- novelty: {opportunity.scores.novelty}\n"
        f"- urgency: {opportunity.scores.urgency}\n"
        f"- founder_fit: {opportunity.scores.founder_fit}\n"
        f"- buildability: {opportunity.scores.buildability}\n"
        f"- monetization: {opportunity.scores.monetization}\n"
        f"- strategic_leverage: {opportunity.scores.strategic_leverage}\n"
    )
    write_artifact(
        workspace_paths,
        artifact_type="opportunity",
        artifact_id=opportunity.id,
        markdown_title=opportunity.title,
        markdown_body=opportunity_body,
        payload={
            **opportunity.model_dump(mode="json"),
            "comparison": comparison,
            "contradictions": contradictions,
            "whitespace": whitespace,
            "updated_at": utc_now(),
        },
    )

    thesis = Thesis(
        id=f"thesis_{slugify(title)}",
        name=title,
        one_line_thesis=(
            f"{title} is a decision-grade system that combines {', '.join(comparison['shared_capabilities'][:2]) or 'strategic signals'} "
            f"with {', '.join(comparison['differentiation_zones'][:2]) or 'a differentiated wedge'} to produce durable product direction."
        ),
        workspace=workspace,
        source_ids=[source.id for source in sources],
        opportunity_id=opportunity.id,
    )
    thesis_body = (
        f"**One-line Thesis:** {thesis.one_line_thesis}\n\n"
        f"**Signal Inputs:** {', '.join(thesis.source_ids)}\n\n"
        f"**Opportunity Anchor:** {thesis.opportunity_id}\n\n"
        f"**Strategic Wedge:** {whitespace['wedge_statement']}\n\n"
        f"**Comparison Summary:** {comparison['comparison_summary']}\n\n"
        f"**Contradictions:**\n" + "\n".join(f"- {item}" for item in contradictions['contradictions'] or ['none']) + "\n"
    )
    write_artifact(
        workspace_paths,
        artifact_type="thesis",
        artifact_id=thesis.id,
        markdown_title=thesis.name,
        markdown_body=thesis_body,
        payload={**thesis.model_dump(mode="json"), "comparison": comparison, "contradictions": contradictions, "whitespace": whitespace, "updated_at": utc_now()},
    )
    typer.echo(thesis.id)


@decide_app.command("commit")
def decide_commit(
    thesis_id: str,
    decision: str = typer.Option(..., "--decision"),
    workspace: str = typer.Option("default", "--workspace"),
    review_after: str | None = typer.Option(None, "--review-after"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace_paths = build_workspace(name=workspace, root=root)
    thesis_payload = load_artifact_json(root, workspace, "thesis", thesis_id)
    thesis = Thesis(**thesis_payload)
    review_date = date.fromisoformat(review_after) if review_after else None
    intelligence = compute_decision_intelligence(thesis_payload)
    memo = DecisionMemo(
        id=f"decision_{decision}_{slugify(thesis.name)}",
        thesis_id=thesis.id,
        decision=decision,
        to_state=decision,
        evidence_ids=[thesis.opportunity_id] if thesis.opportunity_id else [],
        review_after=review_date,
        workspace=workspace,
    )
    body = (
        f"**Thesis:** {thesis.name}\n\n"
        f"**Decision:** {memo.decision}\n\n"
        f"**From State:** {memo.from_state}\n\n"
        f"**To State:** {memo.to_state}\n\n"
        f"**Evidence:** {', '.join(memo.evidence_ids) if memo.evidence_ids else 'none'}\n\n"
        f"**Evidence Density:** {intelligence['evidence_density']}\n\n"
        f"**Contradiction Load:** {intelligence['contradiction_load']}\n\n"
        f"**Confidence Shift:** {intelligence['confidence_before']} → {intelligence['confidence_after']}\n\n"
        f"**Whitespace Score:** {intelligence['whitespace_score']}\n\n"
        f"**Category Pressure:** {intelligence['category_pressure']}\n\n"
        f"**Review After:** {memo.review_after.isoformat() if memo.review_after else 'unscheduled'}\n"
    )
    write_artifact(
        workspace_paths,
        artifact_type="decision",
        artifact_id=memo.id,
        markdown_title=f"Decision for {thesis.name}",
        markdown_body=body,
        payload={**memo.model_dump(mode="json"), "decision_intelligence": intelligence, "updated_at": utc_now()},
    )
    typer.echo(memo.id)


@execution_app.command("brief")
def execution_brief(
    thesis_id: str,
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace_paths = build_workspace(name=workspace, root=root)
    thesis_payload = load_artifact_json(root, workspace, "thesis", thesis_id)
    comparison = thesis_payload.get("comparison", {})
    whitespace = thesis_payload.get("whitespace", {})
    contradictions = thesis_payload.get("contradictions", {})
    artifact_id = f"implementation_brief_{slugify(thesis_id)}"
    body = (
        f"**Target Thesis:** {thesis_payload.get('name', thesis_id)}\n\n"
        f"**Build Objective:** Materialize the wedge '{whitespace.get('wedge_statement', 'none')}'.\n\n"
        f"**Core Modules:**\n"
        f"- intake and source normalization\n"
        f"- comparison and whitespace analysis\n"
        f"- decision intelligence and portfolio memory\n"
        f"- execution and publish surfaces\n\n"
        f"**Shared Strategic Capabilities:** {', '.join(comparison.get('shared_capabilities', [])) or 'none'}\n\n"
        f"**Open Contradictions:**\n" + "\n".join(f"- {item}" for item in contradictions.get('contradictions', []) or ['none']) + "\n"
    )
    payload = {
        "id": artifact_id,
        "workspace": workspace,
        "thesis_id": thesis_id,
        "build_objective": whitespace.get("wedge_statement"),
        "shared_capabilities": comparison.get("shared_capabilities", []),
        "contradictions": contradictions,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    write_artifact(workspace_paths, "experiment", artifact_id, f"Implementation Brief - {thesis_payload.get('name', thesis_id)}", body, payload)
    typer.echo(artifact_id)


@execution_app.command("issue-tree")
def execution_issue_tree(
    thesis_id: str,
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace_paths = build_workspace(name=workspace, root=root)
    thesis_payload = load_artifact_json(root, workspace, "thesis", thesis_id)
    comparison = thesis_payload.get("comparison", {})
    issue_tree = [
        {
            "key": "SF-1",
            "title": "Establish workspace, source models, and artifact persistence",
            "phase": "foundation",
            "depends_on": [],
            "risk_flags": ["schema drift", "workspace inconsistency"],
            "acceptance_criteria": ["artifacts persist predictably", "workspace manifest remains stable"],
            "verification_commands": ["forge workspace init", "forge intake add"],
            "expected_outputs": ["workspace manifest written", "source artifacts created in both markdown and json"],
            "exit_conditions": ["source persistence is deterministic", "workspace topology is stable"],
            "blockers": [],
        },
        {
            "key": "SF-2",
            "title": "Implement comparison, contradiction, and whitespace intelligence",
            "phase": "intelligence",
            "depends_on": ["SF-1"],
            "risk_flags": ["shallow comparison outputs", "false strategic convergence"],
            "acceptance_criteria": ["comparison reveals overlap and differentiation", "contradictions surface explicitly"],
            "verification_commands": ["forge analyze compare", "forge analyze contradictions", "forge analyze whitespaces"],
            "expected_outputs": ["comparison artifact created", "contradiction artifact created", "whitespace opportunity created"],
            "exit_conditions": ["reasoning traces are visible in artifacts", "whitespace wedge is explicitly stated"],
            "blockers": ["SF-1"],
        },
        {
            "key": "SF-3",
            "title": "Implement thesis, decision, and portfolio causality surfaces",
            "phase": "decision",
            "depends_on": ["SF-1", "SF-2"],
            "risk_flags": ["weak causality", "decisions without evidence density"],
            "acceptance_criteria": ["decision artifacts include confidence movement", "portfolio lineage remains traceable"],
            "verification_commands": ["forge thesis create", "forge decide commit", "forge portfolio lineage", "forge portfolio drift"],
            "expected_outputs": ["thesis artifact created", "decision memo contains decision intelligence", "lineage and drift artifacts exist"],
            "exit_conditions": ["decision lineage is auditable", "portfolio state can be reviewed over time"],
            "blockers": ["SF-1", "SF-2"],
        },
        {
            "key": "SF-4",
            "title": "Implement execution bridge artifacts and build planning outputs",
            "phase": "execution",
            "depends_on": ["SF-3"],
            "risk_flags": ["execution artifacts too generic", "missing dependency realism"],
            "acceptance_criteria": ["implementation brief is actionable", "issue tree and roadmap preserve structure"],
            "verification_commands": ["forge execution brief", "forge execution issue-tree", "forge execution plan-pack", "forge execution roadmap"],
            "expected_outputs": ["implementation brief created", "issue tree contains dependencies and gates", "roadmap phases rendered"],
            "exit_conditions": ["delivery structure is internally coherent", "execution artifacts can drive real build motion"],
            "blockers": ["SF-3"],
        },
        {
            "key": "SF-5",
            "title": f"Refine wedge around {', '.join(comparison.get('shared_capabilities', [])[:2]) or 'core strategic capabilities'}",
            "phase": "positioning",
            "depends_on": ["SF-2", "SF-3"],
            "risk_flags": ["category ambiguity", "positioning drift"],
            "acceptance_criteria": ["wedge becomes externally legible", "differentiation survives contradiction review"],
            "verification_commands": ["forge thesis create", "forge portfolio drift"],
            "expected_outputs": ["thesis reflects differentiated wedge", "drift output does not collapse into crowding-risk without cause"],
            "exit_conditions": ["category claim is defensible", "positioning survives portfolio pressure"],
            "blockers": ["SF-2", "SF-3"],
        },
    ]
    artifact_id = f"issue_tree_{slugify(thesis_id)}"
    body = "**Issue Tree:**\n\n" + "\n\n".join(
        f"- {item['key']} [{item['phase']}] depends_on={item['depends_on'] or ['none']}: {item['title']}\n  risk_flags={item['risk_flags']}\n  acceptance_criteria={item['acceptance_criteria']}\n  verification_commands={item['verification_commands']}\n  expected_outputs={item['expected_outputs']}\n  exit_conditions={item['exit_conditions']}\n  blockers={item['blockers'] or ['none']}" for item in issue_tree
    ) + "\n"
    payload = {
        "id": artifact_id,
        "workspace": workspace,
        "thesis_id": thesis_id,
        "issues": issue_tree,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    write_artifact(workspace_paths, "experiment", artifact_id, f"Issue Tree - {thesis_payload.get('name', thesis_id)}", body, payload)
    typer.echo(artifact_id)


@execution_app.command("plan-pack")
def execution_plan_pack(
    thesis_id: str,
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace_paths = build_workspace(name=workspace, root=root)
    brief_id = f"implementation_brief_{slugify(thesis_id)}"
    issue_tree_id = f"issue_tree_{slugify(thesis_id)}"
    if not artifact_exists(root, workspace, "experiment", brief_id):
        execution_brief(thesis_id=thesis_id, workspace=workspace, root=root)
    if not artifact_exists(root, workspace, "experiment", issue_tree_id):
        execution_issue_tree(thesis_id=thesis_id, workspace=workspace, root=root)
    brief_payload = load_artifact_json(root, workspace, "experiment", brief_id)
    issue_tree_payload = load_artifact_json(root, workspace, "experiment", issue_tree_id)
    artifact_id = f"plan_pack_{slugify(thesis_id)}"
    body = (
        f"**Implementation Brief:** {brief_payload['id']}\n\n"
        f"**Issue Tree:** {issue_tree_payload['id']}\n\n"
        f"**Execution Summary:** This plan pack consolidates build objective, dependency structure, blockers, risk flags, and acceptance criteria into one execution surface.\n"
    )
    payload = {
        "id": artifact_id,
        "workspace": workspace,
        "thesis_id": thesis_id,
        "implementation_brief_id": brief_payload["id"],
        "issue_tree_id": issue_tree_payload["id"],
        "issue_count": len(issue_tree_payload.get("issues", [])),
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    write_artifact(workspace_paths, "experiment", artifact_id, f"Plan Pack - {thesis_id}", body, payload)
    typer.echo(artifact_id)


@execution_app.command("review")
def execution_review(
    thesis_id: str,
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace_paths = build_workspace(name=workspace, root=root)
    issue_tree_id = f"issue_tree_{slugify(thesis_id)}"
    if not artifact_exists(root, workspace, "experiment", issue_tree_id):
        execution_issue_tree(thesis_id=thesis_id, workspace=workspace, root=root)
    issue_tree_payload = load_artifact_json(root, workspace, "experiment", issue_tree_id)
    unresolved = [issue["key"] for issue in issue_tree_payload.get("issues", []) if issue.get("blockers")]
    high_risk = [issue["key"] for issue in issue_tree_payload.get("issues", []) if len(issue.get("risk_flags", [])) >= 2]
    readiness = "gated" if unresolved else "clear"
    artifact_id = f"execution_review_{slugify(thesis_id)}"
    body = (
        f"**Readiness:** {readiness}\n\n"
        f"**Unresolved Gates:** {', '.join(unresolved) or 'none'}\n\n"
        f"**High-Risk Work Items:** {', '.join(high_risk) or 'none'}\n\n"
        f"**Review Result:** {'Execution is still constrained by dependency or blocker pressure.' if unresolved else 'Execution surface is structurally clear.'}\n"
    )
    payload = {
        "id": artifact_id,
        "workspace": workspace,
        "thesis_id": thesis_id,
        "readiness": readiness,
        "unresolved_gates": unresolved,
        "high_risk_work_items": high_risk,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    write_artifact(workspace_paths, "experiment", artifact_id, f"Execution Review - {thesis_id}", body, payload)
    typer.echo(artifact_id)


@execution_app.command("roadmap")
def execution_roadmap(
    thesis_id: str,
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace_paths = build_workspace(name=workspace, root=root)
    thesis_payload = load_artifact_json(root, workspace, "thesis", thesis_id)
    comparison = thesis_payload.get("comparison", {})
    whitespace = thesis_payload.get("whitespace", {})
    roadmap = [
        {
            "phase": "Phase 1",
            "name": "Foundational substrate",
            "outcome": "Workspace, artifact store, and canonical source graph are durable and consistent.",
            "includes": ["workspace state", "source persistence", "artifact renderer"],
        },
        {
            "phase": "Phase 2",
            "name": "Strategic reasoning core",
            "outcome": "Comparison, contradiction, and whitespace engines shape stronger theses.",
            "includes": ["comparison engine", "contradiction extraction", "opportunity scoring"],
        },
        {
            "phase": "Phase 3",
            "name": "Decision and portfolio memory",
            "outcome": "Decisions become auditable and portfolio drift becomes visible.",
            "includes": ["decision intelligence", "lineage", "drift review"],
        },
        {
            "phase": "Phase 4",
            "name": "Execution and outward force",
            "outcome": f"The wedge '{whitespace.get('wedge_statement', 'core strategic wedge')}' turns into implementation structure and publishable product surface.",
            "includes": ["implementation briefs", "issue trees", "publish packs", f"positioning around {', '.join(comparison.get('shared_capabilities', [])[:2]) or 'core capabilities'}"],
        },
    ]
    artifact_id = f"roadmap_{slugify(thesis_id)}"
    body = "**Execution Roadmap:**\n\n" + "\n\n".join(
        f"### {item['phase']} — {item['name']}\n**Outcome:** {item['outcome']}\n**Includes:** {', '.join(item['includes'])}" for item in roadmap
    ) + "\n"
    payload = {
        "id": artifact_id,
        "workspace": workspace,
        "thesis_id": thesis_id,
        "roadmap": roadmap,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    write_artifact(workspace_paths, "experiment", artifact_id, f"Execution Roadmap - {thesis_payload.get('name', thesis_id)}", body, payload)
    typer.echo(artifact_id)


@export_app.command("readme")
def export_readme(
    thesis_id: str,
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace_paths = build_workspace(name=workspace, root=root)
    thesis_payload = load_artifact_json(root, workspace, "thesis", thesis_id)
    comparison = thesis_payload.get("comparison", {})
    contradictions = thesis_payload.get("contradictions", {})
    whitespace = thesis_payload.get("whitespace", {})
    architecture_snippet = {
        "domains": ["intake", "analysis", "decision", "execution", "export"],
        "core_flow": ["sources", "comparison", "thesis", "decision", "plan pack", "publish pack"],
    }
    example_artifact_snippet = {
        "source_example": thesis_payload.get("source_ids", [])[:2],
        "shared_capabilities": comparison.get("shared_capabilities", [])[:3],
        "wedge": whitespace.get("wedge_statement"),
    }
    launch_snippets = {
        "headline": f"{thesis_payload.get('name', thesis_id)} turns strategic inputs into build decisions.",
        "tagline": "From signals to thesis to execution.",
        "social": f"{thesis_payload.get('name', thesis_id)} converts repos, papers, and ideas into decision-grade artifacts and execution surfaces.",
    }
    readme_id = f"public_readme_{slugify(thesis_id)}"
    body = (
        f"# {thesis_payload.get('name', thesis_id)}\n\n"
        f"**{thesis_payload.get('one_line_thesis', '')}**\n\n"
        f"## Why it exists\n"
        f"{whitespace.get('wedge_statement', 'This product exists to turn strategic inputs into durable direction.')}\n\n"
        f"## Core capabilities\n"
        + "\n".join(f"- {item}" for item in comparison.get('shared_capabilities', [])[:5] or ['decision-grade synthesis'])
        + "\n\n## Architecture surface\n"
        + "\n".join(f"- {item}" for item in architecture_snippet['domains'])
        + "\n\n## Example artifact shape\n"
        + f"- sources: {example_artifact_snippet['source_example']}\n- wedge: {example_artifact_snippet['wedge']}\n"
        + "\n## Category claim\n"
        + "A system that turns strategic inputs into product direction, execution structure, and public-ready artifacts.\n"
        + "\n## Strategic tensions\n"
        + "\n".join(f"- {item}" for item in contradictions.get('contradictions', [])[:3] or ['none'])
        + "\n"
    )
    payload = {
        "id": readme_id,
        "workspace": workspace,
        "thesis_id": thesis_id,
        "content": body,
        "architecture_snippet": architecture_snippet,
        "example_artifact_snippet": example_artifact_snippet,
        "launch_snippets": launch_snippets,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    write_artifact(workspace_paths, "export", readme_id, f"README Export - {thesis_payload.get('name', thesis_id)}", body, payload)
    typer.echo(readme_id)


@export_app.command("publish-pack")
def export_publish_pack(
    thesis_id: str,
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace_paths = build_workspace(name=workspace, root=root)
    if not artifact_exists(root, workspace, "experiment", f"plan_pack_{slugify(thesis_id)}"):
        execution_plan_pack(thesis_id=thesis_id, workspace=workspace, root=root)
    if not artifact_exists(root, workspace, "export", f"public_readme_{slugify(thesis_id)}"):
        export_readme(thesis_id=thesis_id, workspace=workspace, root=root)
    thesis_payload = load_artifact_json(root, workspace, "thesis", thesis_id)
    readme_payload = load_artifact_json(root, workspace, "export", f"public_readme_{slugify(thesis_id)}")
    plan_pack_payload = load_artifact_json(root, workspace, "experiment", f"plan_pack_{slugify(thesis_id)}")
    artifact_id = f"publish_pack_{slugify(thesis_id)}"
    body = (
        f"**Public Surface for:** {thesis_payload.get('name', thesis_id)}\n\n"
        f"**README Export:** {readme_payload['id']}\n\n"
        f"**Plan Pack:** {plan_pack_payload['id']}\n\n"
        f"**Architecture Snippet:** {readme_payload.get('architecture_snippet', {})}\n\n"
        f"**Launch Snippets:** {readme_payload.get('launch_snippets', {})}\n\n"
        f"**Public Package Includes:**\n"
        f"- repository narrative\n"
        f"- category framing\n"
        f"- execution shape summary\n"
        f"- example artifact excerpt\n"
        f"- launch copy snippets\n"
        f"- sanitized artifact lineage for external presentation\n"
    )
    payload = {
        "id": artifact_id,
        "workspace": workspace,
        "thesis_id": thesis_id,
        "readme_export_id": readme_payload["id"],
        "plan_pack_id": plan_pack_payload["id"],
        "architecture_snippet": readme_payload.get("architecture_snippet", {}),
        "example_artifact_snippet": readme_payload.get("example_artifact_snippet", {}),
        "launch_snippets": readme_payload.get("launch_snippets", {}),
        "public_components": ["readme", "category_claim", "execution_shape", "artifact_examples", "launch_snippets"],
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    write_artifact(workspace_paths, "export", artifact_id, f"Publish Pack - {thesis_payload.get('name', thesis_id)}", body, payload)
    typer.echo(artifact_id)


@evidence_app.command("audit")
def evidence_audit(
    thesis_id: str,
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace_paths = build_workspace(name=workspace, root=root)
    thesis_payload = load_artifact_json(root, workspace, "thesis", thesis_id)
    audit = evidence_audit_payload(root, workspace, thesis_payload)
    artifact_id = f"audit_{slugify(thesis_id)}"
    body = (
        f"**Target Thesis:** {thesis_payload.get('name', thesis_id)}\n\n"
        f"**Bundle Health:** {audit['bundle_health']}\n\n"
        f"**Freshness Score:** {audit['freshness_score']}\n\n"
        f"**Provenance Score:** {audit['provenance_score']}\n\n"
        f"**Convergence Score:** {audit['convergence_score']} ({audit['convergence_state']})\n\n"
        f"**Shared Support Features:** {', '.join(audit['shared_support_features']) or 'none'}\n\n"
        f"**Cross-Type Support Features:** {', '.join(audit['cross_type_support_features']) or 'none'}\n\n"
        f"**Convergence Summary:** {audit['convergence_summary']}\n\n"
        f"**Source Diversity Score:** {audit['source_diversity_score']}\n\n"
        f"**Average Source Age (days):** {audit['average_source_age_days']}\n\n"
        f"**Contradiction Score:** {audit['contradiction_score']}\n\n"
        f"**Coverage Score:** {audit['coverage_score']}\n\n"
        f"**Evidence Gaps:**\n"
        + "\n".join(f"- {item}" for item in audit["evidence_gaps"] or ["none"])
        + "\n\n**Hard Triggers:**\n"
        + "\n".join(f"- {item}" for item in audit["hard_triggers"] or ["none"])
        + "\n\n**Soft Triggers:**\n"
        + "\n".join(f"- {item}" for item in audit["soft_triggers"] or ["none"])
        + f"\n\n**Recommended Action:** {audit['recommended_action']}\n\n"
        + f"**Review After:** {audit['review_after']}\n"
    )
    payload = {
        "id": artifact_id,
        "workspace": workspace,
        **audit,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    write_artifact(workspace_paths, "portfolio", artifact_id, f"Evidence Audit - {thesis_payload.get('name', thesis_id)}", body, payload)
    typer.echo(artifact_id)


@portfolio_app.command("lineage")
def portfolio_lineage(
    thesis_id: str,
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace_paths = build_workspace(name=workspace, root=root)
    thesis_payload = load_artifact_json(root, workspace, "thesis", thesis_id)
    source_ids = thesis_payload.get("source_ids", [])
    comparison = thesis_payload.get("comparison", {})
    whitespace = thesis_payload.get("whitespace", {})
    decisions = []
    for path in sorted(workspace_paths.artifact_dir("decision").glob("*.json")):
        payload = load_json(path)
        if payload.get("thesis_id") == thesis_id:
            decisions.append(payload)
    artifact_id = f"lineage_{slugify(thesis_id)}"
    body = (
        f"**Thesis:** {thesis_payload.get('name', thesis_id)}\n\n"
        f"**Source Lineage:**\n" + "\n".join(f"- {item}" for item in source_ids or ["none"]) + "\n\n"
        f"**Shared Capabilities:** {', '.join(comparison.get('shared_capabilities', [])) or 'none'}\n\n"
        f"**Differentiation Zones:** {', '.join(comparison.get('differentiation_zones', [])) or 'none'}\n\n"
        f"**Whitespace Wedge:** {whitespace.get('wedge_statement', 'none')}\n\n"
        f"**Decision Trail:**\n" + "\n".join(f"- {item['id']} -> {item['decision']}" for item in decisions or [{"id":"none","decision":"none"}]) + "\n"
    )
    payload = {
        "id": artifact_id,
        "workspace": workspace,
        "thesis_id": thesis_id,
        "source_ids": source_ids,
        "decision_ids": [item["id"] for item in decisions],
        "comparison": comparison,
        "whitespace": whitespace,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    write_artifact(workspace_paths, "portfolio", artifact_id, f"Lineage - {thesis_payload.get('name', thesis_id)}", body, payload)
    typer.echo(artifact_id)


@portfolio_app.command("themes")
def portfolio_themes(
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace_paths = build_workspace(name=workspace, root=root)
    theses = [load_json(path) for path in sorted(workspace_paths.artifact_dir("thesis").glob("*.json"))]
    theme_intelligence = build_theme_intelligence(theses)
    artifact_id = f"portfolio_themes_{workspace}"
    body = (
        "**Dominant Themes:**\n"
        + "\n".join(
            f"- {item['theme']}: {item['count']}"
            for item in theme_intelligence["dominant_themes"] or [{"theme": "none", "count": 0}]
        )
        + "\n\n"
        + f"**Theme Concentration:** {theme_intelligence['theme_concentration']}\n\n"
        + f"**Theme HHI:** {theme_intelligence['theme_hhi']}\n\n"
        + f"**Concentration State:** {theme_intelligence['concentration_state']}\n\n"
        + "**Theme Clusters:**\n"
        + "\n".join(
            f"- {cluster['cluster_theme']}: {cluster['cluster_size']} theses -> {cluster['thesis_names']}"
            for cluster in theme_intelligence["clusters"] or [{"cluster_theme": "none", "cluster_size": 0, "thesis_names": []}]
        )
        + "\n\n**Concentration Risks:**\n"
        + "\n".join(
            f"- {risk['theme']}: share={risk['share']} across {risk['thesis_count']} theses"
            for risk in theme_intelligence["concentration_risks"] or [{"theme": "none", "share": 0.0, "thesis_count": 0}]
        )
        + "\n\n**Merge Candidates:**\n"
        + "\n".join(
            f"- {item['names'][0]} <> {item['names'][1]} :: overlap={item['overlap_ratio']} uplift={item['merge_uplift']} shared={item['shared_themes']}"
            for item in theme_intelligence["merge_candidates"]
            or [{"names": ["none", "none"], "overlap_ratio": 0.0, "merge_uplift": 0.0, "shared_themes": []}]
        )
        + "\n\n**Bridge Themes:**\n"
        + "\n".join(
            f"- {item['theme']}: spans {item['cluster_count']} clusters -> {item['clusters']}"
            for item in theme_intelligence["bridge_themes"] or [{"theme": "none", "cluster_count": 0, "clusters": []}]
        )
        + "\n\n**Whitespace Themes:**\n"
        + "\n".join(f"- {theme}" for theme in theme_intelligence["whitespace_themes"] or ["none"])
        + "\n\n**Diversification Targets:**\n"
        + "\n".join(
            f"- {item['name']}: {item['theme']} -> {item['reason']}"
            for item in theme_intelligence["diversification_targets"] or [{"name": "none", "theme": "none", "reason": "none"}]
        )
        + "\n\n**Thesis Theme Map:**\n"
        + "\n".join(
            f"- {item['name']}: {item['themes']}"
            for item in theme_intelligence["thesis_themes"] or [{"name": "none", "themes": []}]
        )
        + "\n"
    )
    payload = {
        "id": artifact_id,
        "workspace": workspace,
        **theme_intelligence,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    write_artifact(workspace_paths, "portfolio", artifact_id, f"Portfolio Themes - {workspace}", body, payload)
    typer.echo(artifact_id)


@portfolio_app.command("drift")
def portfolio_drift(
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace_paths = build_workspace(name=workspace, root=root)
    theses = [load_json(path) for path in sorted(workspace_paths.artifact_dir("thesis").glob("*.json"))]
    drift_items = []
    for thesis_payload in theses:
        comparison = thesis_payload.get("comparison", {})
        whitespace = thesis_payload.get("whitespace", {})
        overlap = float(comparison.get("overlap_strength", 0.0) or 0.0)
        diff_count = len(comparison.get("differentiation_zones", []))
        whitespace_score = float(whitespace.get("whitespace_score", 0.0) or 0.0)
        if overlap >= 0.5 and diff_count <= 2:
            state = "crowding-risk"
        elif whitespace_score >= 8.0 and diff_count >= 3:
            state = "expansion-open"
        else:
            state = "stable"
        drift_items.append({
            "thesis_id": thesis_payload["id"],
            "name": thesis_payload.get("name"),
            "overlap_strength": overlap,
            "differentiation_count": diff_count,
            "whitespace_score": whitespace_score,
            "drift_state": state,
        })
    artifact_id = f"portfolio_drift_{workspace}"
    body = "**Drift Review:**\n\n" + "\n".join(
        f"- {item['name']} :: {item['drift_state']} (overlap={item['overlap_strength']}, whitespace={item['whitespace_score']})"
        for item in drift_items or [{"name":"none","drift_state":"none","overlap_strength":0,"whitespace_score":0}]
    ) + "\n"
    payload = {
        "id": artifact_id,
        "workspace": workspace,
        "items": drift_items,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    write_artifact(workspace_paths, "portfolio", artifact_id, f"Portfolio Drift - {workspace}", body, payload)
    typer.echo(artifact_id)


@portfolio_app.command("review")
def portfolio_review(
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace_paths = build_workspace(name=workspace, root=root)
    theses = load_artifact_collection(workspace_paths, "thesis")
    decisions = load_artifact_collection(workspace_paths, "decision")
    experiments = load_artifact_collection(workspace_paths, "experiment")
    decisions_by_thesis = {
        thesis_payload["id"]: [payload for payload in decisions if payload.get("thesis_id") == thesis_payload["id"]]
        for thesis_payload in theses
    }
    execution_by_thesis = {
        thesis_payload["id"]: [payload for payload in experiments if payload.get("thesis_id") == thesis_payload["id"]]
        for thesis_payload in theses
    }
    audits = {
        thesis_payload["id"]: evidence_audit_payload(root, workspace, thesis_payload)
        for thesis_payload in theses
    }
    review = build_portfolio_review(theses, audits, decisions_by_thesis, execution_by_thesis)
    artifact_id = f"portfolio_review_{workspace}"
    lane_lines = [
        f"- {item['name']}: {item['lane']} (conviction={item['conviction_score']}, confidence={item['confidence_score']}, theme_overlap={item.get('theme_overlap', 0.0)})"
        for item in review["lane_assignments"]
    ] or ["- none"]
    drift_lines = [
        f"- {item['thesis_id']}: {item['drift_type']} / {item['severity']} -> {item['recommended_action']}"
        for item in review["drift_alerts"]
    ] or ["- none"]
    gap_lines = [f"- {item['thesis_id']}: {item['gap']}" for item in review["execution_gaps"]] or ["- none"]
    merge_lines = [
        f"- {item['names'][0]} <> {item['names'][1]} :: uplift={item['merge_uplift']} shared={item['shared_themes']}"
        for item in review["merge_opportunities"]
    ] or ["- none"]
    diversification_lines = [
        f"- {item['name']}: {item['theme']}"
        for item in review["diversification_targets"]
    ] or ["- none"]
    action_lines = [f"- {item['action']}: {item['target_id']}" for item in review["actions"]] or ["- none"]
    body = (
        f"**Workspace:** {workspace}\n\n"
        f"**Summary:** {review['summary']}\n\n"
        + f"**Theme Concentration State:** {review['theme_intelligence']['concentration_state']}\n\n"
        + "**Lane Assignments:**\n" + "\n".join(lane_lines)
        + "\n\n**Merge Opportunities:**\n" + "\n".join(merge_lines)
        + "\n\n**Diversification Targets:**\n" + "\n".join(diversification_lines)
        + "\n\n**Drift Alerts:**\n" + "\n".join(drift_lines)
        + "\n\n**Execution Gaps:**\n" + "\n".join(gap_lines)
        + "\n\n**Actions:**\n" + "\n".join(action_lines) + "\n"
    )
    payload = {
        "id": artifact_id,
        "workspace": workspace,
        **review,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    write_artifact(workspace_paths, "portfolio", artifact_id, f"Portfolio Review - {workspace}", body, payload)
    typer.echo(artifact_id)


@portfolio_app.command("rebalance")
def portfolio_rebalance(
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace_paths = build_workspace(name=workspace, root=root)
    review_path = workspace_paths.artifact_dir("portfolio") / f"portfolio_review_{workspace}.json"
    if review_path.exists():
        review_payload = load_json(review_path)
    else:
        theses = load_artifact_collection(workspace_paths, "thesis")
        decisions = load_artifact_collection(workspace_paths, "decision")
        experiments = load_artifact_collection(workspace_paths, "experiment")
        decisions_by_thesis = {
            thesis_payload["id"]: [payload for payload in decisions if payload.get("thesis_id") == thesis_payload["id"]]
            for thesis_payload in theses
        }
        execution_by_thesis = {
            thesis_payload["id"]: [payload for payload in experiments if payload.get("thesis_id") == thesis_payload["id"]]
            for thesis_payload in theses
        }
        audits = {
            thesis_payload["id"]: evidence_audit_payload(root, workspace, thesis_payload)
            for thesis_payload in theses
        }
        review_payload = build_portfolio_review(theses, audits, decisions_by_thesis, execution_by_thesis)
    rebalance = build_portfolio_rebalance(review_payload)
    artifact_id = f"portfolio_rebalance_{workspace}"
    body = (
        "**Attention Moves:**\n"
        + "\n".join(
            f"- {item['name']}: {item['attention_shift']} ({item['current_lane']})"
            for item in rebalance["attention_moves"]
        )
        + "\n\n**Priority Order:**\n"
        + "\n".join(f"- {item}" for item in rebalance["priority_order"] or ["none"])
        + "\n\n**Review Priorities:**\n"
        + "\n".join(f"- {item}" for item in rebalance["review_priorities"] or ["none"])
        + "\n\n**Merge Suggestions:**\n"
        + "\n".join(
            f"- {item['pair'][0]} <> {item['pair'][1]} :: uplift={item['merge_uplift']} shared={item['shared_themes']}"
            for item in rebalance["merge_suggestions"]
            if isinstance(item, dict)
        )
        + ("" if any(isinstance(item, dict) for item in rebalance["merge_suggestions"]) else "- none")
        + "\n\n**Concentration Moves:**\n"
        + "\n".join(
            f"- {item['theme']}: {item['motion']} -> {item['reason']}"
            for item in rebalance["concentration_moves"] or [{"theme": "none", "motion": "none", "reason": "none"}]
        )
        + "\n\n**Diversification Targets:**\n"
        + "\n".join(
            f"- {item['name']}: {item['theme']}"
            for item in rebalance["diversification_targets"] or [{"name": "none", "theme": "none"}]
        )
        + "\n"
    )
    payload = {
        "id": artifact_id,
        "workspace": workspace,
        **rebalance,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    write_artifact(workspace_paths, "portfolio", artifact_id, f"Portfolio Rebalance - {workspace}", body, payload)
    typer.echo(artifact_id)


@portfolio_app.command("map")
def portfolio_map(
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    workspace_paths = build_workspace(name=workspace, root=root)
    theses = sorted(workspace_paths.artifact_dir("thesis").glob("*.json"))
    decisions = sorted(workspace_paths.artifact_dir("decision").glob("*.json"))
    artifact_id = f"portfolio_map_{workspace}"
    thesis_lines = [load_json(path)["id"] for path in theses]
    decision_lines = [load_json(path)["id"] for path in decisions]
    body = (
        f"**Workspace:** {workspace}\n\n"
        f"**Theses:**\n" + "\n".join(f"- {item}" for item in thesis_lines or ["none"]) + "\n\n"
        f"**Decisions:**\n" + "\n".join(f"- {item}" for item in decision_lines or ["none"]) + "\n"
    )
    payload = {
        "id": artifact_id,
        "workspace": workspace,
        "thesis_ids": thesis_lines,
        "decision_ids": decision_lines,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    write_artifact(
        workspace_paths,
        artifact_type="portfolio",
        artifact_id=artifact_id,
        markdown_title=f"Portfolio Map - {workspace}",
        markdown_body=body,
        payload=payload,
    )
    typer.echo(artifact_id)


# ── Adversarial Engine CLI ──────────────────────────────────────────
adversarial_app = typer.Typer(help="Adversarial Thesis Engine (Red Team AI)")
app.add_typer(adversarial_app, name="adversarial")


@adversarial_app.command("audit")
def adversarial_audit(
    thesis_id: str = typer.Argument(help="Thesis artifact ID"),
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    """Run adversarial audit: kill criteria + red team + bias check."""
    from signalforge.adversarial.engine import AdversarialEngine

    thesis_payload = load_artifact_json(root, workspace, "thesis", thesis_id)
    engine = AdversarialEngine(provider=_get_semantic_provider())
    result = engine.audit_thesis(thesis_payload)
    colors = {"green": "🟢", "yellow": "🟡", "orange": "🟠", "red": "🔴"}
    typer.echo(f"{colors.get(result['status'], '⚪')} {thesis_id}: {result['status'].upper()}")
    typer.echo(f"  Vulnerability: {result['vulnerability_score']} | Kill Criteria: {result['kill_criteria_triggered']}/{result['kill_criteria_total']}")
    if result.get("anti_thesis"):
        typer.echo(f"  Anti-Thesis: {result['anti_thesis'][:150]}...")
    typer.echo(f"  → {result['recommendation']}")


@adversarial_app.command("stress-test")
def adversarial_stress_test(
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    """Portfolio-level stress test across all theses."""
    from signalforge.adversarial.engine import AdversarialEngine

    ws = build_workspace(name=workspace, root=root)
    theses = [load_json(p) for p in sorted(ws.artifact_dir("thesis").glob("*.json"))]
    if not theses:
        typer.echo("No theses found.")
        return
    engine = AdversarialEngine(provider=_get_semantic_provider())
    result = engine.portfolio_stress_test(theses)
    colors = {"green": "🟢", "yellow": "🟡", "orange": "🟠", "red": "🔴"}
    typer.echo(f"{colors.get(result['portfolio_alert_level'], '⚪')} Portfolio: {len(theses)} theses, risk={result['composite_risk']}")
    typer.echo(f"  At risk: {result['theses_at_risk']} | Bias: {result['bias_health']}")
    typer.echo(f"  → {result['recommendation']}")


@adversarial_app.command("red-team")
def adversarial_red_team(
    thesis_id: str = typer.Argument(help="Thesis artifact ID"),
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    """Build strongest argument AGAINST a thesis."""
    from signalforge.adversarial.red_team import RedTeamBuilder

    thesis_payload = load_artifact_json(root, workspace, "thesis", thesis_id)
    builder = RedTeamBuilder(_get_semantic_provider())
    result = builder.build_red_team(thesis_payload)
    if not result:
        typer.echo("Red team failed.")
        return
    typer.echo(f"⚔️ Red Team: {thesis_id}")
    typer.echo(f"  Anti-Thesis: {result.get('anti_thesis', 'N/A')[:200]}")
    typer.echo(f"  Vulnerability: {result.get('overall_vulnerability_score', 'N/A')}")
    typer.echo(f"  Steel-Man: {result.get('steel_man_opposition', 'N/A')[:200]}")
    for a in result.get("load_bearing_assumptions", []):
        typer.echo(f"  ⚠ {a.get('assumption', '?')} (fail prob: {a.get('failure_probability', '?')})")
    for m in result.get("failure_modes", []):
        typer.echo(f"  ✗ {m.get('mode', '?')}: {m.get('description', '')[:80]}")


@adversarial_app.command("bias-audit")
def adversarial_bias_audit(
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    """Audit confirmation bias across all theses."""
    from signalforge.adversarial.bias_tracker import BiasTracker

    ws = build_workspace(name=workspace, root=root)
    theses = [load_json(p) for p in sorted(ws.artifact_dir("thesis").glob("*.json"))]
    if not theses:
        typer.echo("No theses found.")
        return
    audit = BiasTracker.portfolio_bias_audit(theses)
    colors = {"healthy": "🟢", "warning": "🟡", "critical": "🔴"}
    typer.echo(f"{colors.get(audit['overall_health'], '⚪')} Bias Audit: {audit['total_theses']} theses, {audit['theses_with_bias']} biased")
    for b in audit.get("biases_found", []):
        typer.echo(f"  [{b['severity']}] {b['bias_type']} → {b['thesis_id']}: {b['detail'][:80]}")


# ── SignalDrift CLI ────────────────────────────────────────────────
drift_app = typer.Typer(help="SignalDrift Engine - Temporal Signal Dynamics")
app.add_typer(drift_app, name="drift")


@drift_app.command("snapshot")
def drift_snapshot(
    thesis_id: str = typer.Argument(help="Thesis artifact ID"),
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    """Record a signal snapshot for a thesis."""
    from signalforge.drift.timeseries import TimeSeriesStore
    from signalforge.drift.analyzer import DriftAnalyzer

    thesis_payload = load_artifact_json(root, workspace, "thesis", thesis_id)
    store = TimeSeriesStore()
    snapshot = store.record_thesis(thesis_payload)
    typer.echo(f"📸 Snapshot recorded: {thesis_id}")
    typer.echo(f"  Composite: {snapshot.composite_score()}")
    typer.echo(f"  Timestamp: {snapshot.timestamp}")


@drift_app.command("analyze")
def drift_analyze(
    thesis_id: str = typer.Argument(help="Thesis artifact ID"),
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    """Analyze drift dynamics for a thesis."""
    from signalforge.drift.timeseries import TimeSeriesStore, SignalSnapshot
    from signalforge.drift.analyzer import DriftAnalyzer
    from signalforge.drift.classifier import SignalClassifier

    ws = build_workspace(name=workspace, root=root)
    theses = [load_json(p) for p in sorted(ws.artifact_dir("thesis").glob("*.json"))]
    if not theses:
        typer.echo("No theses found.")
        return

    store = TimeSeriesStore()
    for t in theses:
        if t.get("id") == thesis_id or not thesis_id:
            store.record_thesis(t)
            # Record from history if available
            for _ in range(2):
                store.record_thesis(t)

    analyzer = DriftAnalyzer(store)
    vector = analyzer.analyze(thesis_id)
    cls = SignalClassifier.classify(vector.to_dict())

    phase_colors = {"emerging": "🟢", "strengthening": "📈", "stable": "⚖️", "decaying": "📉", "dormant": "💤", "divergent": "🔀"}
    icon = phase_colors.get(cls.phase.value, "⚪")
    typer.echo(f"{icon} {thesis_id}: {cls.phase.value.upper()}")
    typer.echo(f"  Momentum: {vector.momentum:.3f} | Volatility: {vector.volatility:.3f}")
    typer.echo(f"  Snapshots: {vector.snapshot_count} | Confidence: {cls.confidence}")
    typer.echo(f"  → {cls.recommended_action}")


@drift_app.command("portfolio")
def drift_portfolio(
    workspace: str = typer.Option("default", "--workspace"),
    root: Path = typer.Option(default_factory=default_root, file_okay=False, dir_okay=True, resolve_path=True),
) -> None:
    """Full portfolio drift overview."""
    from signalforge.drift.timeseries import TimeSeriesStore
    from signalforge.drift.analyzer import DriftAnalyzer
    from signalforge.drift.classifier import SignalClassifier

    ws = build_workspace(name=workspace, root=root)
    theses = [load_json(p) for p in sorted(ws.artifact_dir("thesis").glob("*.json"))]
    if not theses:
        typer.echo("No theses found.")
        return

    store = TimeSeriesStore()
    for t in theses:
        for _ in range(3):
            store.record_thesis(t)

    analyzer = DriftAnalyzer(store)
    result = analyzer.analyze_portfolio()

    typer.echo(f"📊 Portfolio Drift: {result['total_theses']} signals")
    for cls_name, count in result["classifications"].items():
        typer.echo(f"  {cls_name}: {count}")
    typer.echo(f"  Highest momentum: {result['highest_momentum']}")
    typer.echo(f"  Most volatile: {result['most_volatile']}")


if __name__ == "__main__":
    app()
