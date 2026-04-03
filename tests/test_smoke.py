from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path

from typer.testing import CliRunner

from signalforge.cli.main import app, infer_freshness_score
from signalforge.analysis import audit_evidence_bundle, build_portfolio_rebalance, build_portfolio_review, build_theme_intelligence
from signalforge.models import DecisionMemo, PublishPack


runner = CliRunner()


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "SignalForge 0.1.0" in result.stdout


def test_artifact_types_command() -> None:
    result = runner.invoke(app, ["artifact-types"])
    assert result.exit_code == 0
    assert "publish-pack" in result.stdout
    assert "product-thesis" in result.stdout


def test_decision_states_command() -> None:
    result = runner.invoke(app, ["decision-states"])
    assert result.exit_code == 0
    assert "revisit" in result.stdout
    assert "build" in result.stdout


def test_models_capture_decision_and_publish_pack_shapes() -> None:
    decision = DecisionMemo(
        id="decision_build_signalforge-001",
        thesis_id="thesis_signalforge-001",
        decision="build",
        to_state="build",
        evidence_ids=["opp_001", "insight_003"],
        review_after=date(2026, 5, 20),
        workspace="signalforge-lab",
    )
    publish_pack = PublishPack(
        id="publish_pack_001",
        workspace="signalforge-lab",
        target="github_open_source_launch",
        source_artifacts=[decision.id],
    )

    assert decision.to_state == "build"
    assert publish_pack.narrative_mode == "category-defining"
    assert publish_pack.remove_private_notes is True


def test_workspace_flow_creates_real_artifacts(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / ".signalforge"

    from signalforge.cli import main as cli_main

    monkeypatch.setattr(
        cli_main,
        "fetch_github_repo_metadata",
        lambda input_value: {
            "github_owner": "example",
            "github_repo": "repo",
            "stars": "12345",
            "forks": "321",
            "language": "Python",
            "repo_description": "Agent workflow and research graph engine",
            "updated_at": "2026-04-02T00:00:00Z",
        }
        if "github.com" in input_value
        else {},
    )
    monkeypatch.setattr(
        cli_main,
        "fetch_article_metadata",
        lambda input_value: {
            "hostname": "example.com",
            "path": "/article",
            "page_title": "Strategic Article",
        }
        if "example.com/article" in input_value
        else {},
    )
    monkeypatch.setattr(
        cli_main,
        "fetch_arxiv_metadata",
        lambda input_value: {
            "paper_id": "1234.5678",
            "paper_title": "Strategic Paper",
            "paper_summary": "Paper summary",
            "paper_authors": "Jane Doe, John Roe",
            "paper_source": "arxiv",
        }
        if "arxiv.org/abs/1234.5678" in input_value
        else {},
    )

    result = runner.invoke(app, ["workspace", "init", "lab", "--root", str(root)])
    assert result.exit_code == 0

    source_specs = [
        ("https://github.com/example/repo", "repo", "Example Repo", "Repository for testing SignalForge"),
        ("https://example.com/article", "article", "Strategic Article", "Article describing market and workflow shifts"),
        ("https://arxiv.org/abs/1234.5678", "paper", "Agent Paper", "Paper describing agent coordination patterns"),
    ]
    source_ids: list[str] = []
    for input_value, source_type, title, summary in source_specs:
        result = runner.invoke(
            app,
            [
                "intake",
                "add",
                input_value,
                "--type",
                source_type,
                "--workspace",
                "lab",
                "--title",
                title,
                "--summary",
                summary,
                "--root",
                str(root),
            ],
        )
        assert result.exit_code == 0
        source_ids.append(result.stdout.strip())

    result = runner.invoke(
        app,
        ["analyze", "source", source_ids[0], "--workspace", "lab", "--root", str(root)],
    )
    assert result.exit_code == 0
    insight_id = result.stdout.strip()
    assert insight_id.startswith("insight_")

    result = runner.invoke(
        app,
        [
            "analyze",
            "compare",
            "--source",
            source_ids[0],
            "--source",
            source_ids[1],
            "--source",
            source_ids[2],
            "--workspace",
            "lab",
            "--root",
            str(root),
        ],
    )
    assert result.exit_code == 0
    comparison_id = result.stdout.strip()
    assert comparison_id.startswith("comparison_")

    result = runner.invoke(
        app,
        [
            "analyze",
            "contradictions",
            "--source",
            source_ids[0],
            "--source",
            source_ids[1],
            "--source",
            source_ids[2],
            "--workspace",
            "lab",
            "--root",
            str(root),
        ],
    )
    assert result.exit_code == 0
    contradiction_id = result.stdout.strip()
    assert contradiction_id.startswith("contradictions_")

    result = runner.invoke(
        app,
        [
            "analyze",
            "whitespaces",
            "--source",
            source_ids[0],
            "--source",
            source_ids[1],
            "--source",
            source_ids[2],
            "--title",
            "Strategic Signal Engine",
            "--workspace",
            "lab",
            "--root",
            str(root),
        ],
    )
    assert result.exit_code == 0
    whitespace_opp_id = result.stdout.strip()
    assert whitespace_opp_id == "opp_strategic-signal-engine"

    result = runner.invoke(
        app,
        [
            "thesis",
            "create",
            "--source",
            source_ids[0],
            "--source",
            source_ids[1],
            "--source",
            source_ids[2],
            "--title",
            "Signal Graph Engine",
            "--workspace",
            "lab",
            "--root",
            str(root),
        ],
    )
    assert result.exit_code == 0
    thesis_id = result.stdout.strip()

    result = runner.invoke(
        app,
        [
            "decide",
            "commit",
            thesis_id,
            "--decision",
            "build",
            "--workspace",
            "lab",
            "--review-after",
            "2026-05-20",
            "--root",
            str(root),
        ],
    )
    assert result.exit_code == 0
    decision_id = result.stdout.strip()

    result = runner.invoke(
        app,
        ["execution", "brief", thesis_id, "--workspace", "lab", "--root", str(root)],
    )
    assert result.exit_code == 0
    brief_id = result.stdout.strip()
    assert brief_id.startswith("implementation_brief_")

    result = runner.invoke(
        app,
        ["execution", "issue-tree", thesis_id, "--workspace", "lab", "--root", str(root)],
    )
    assert result.exit_code == 0
    issue_tree_id = result.stdout.strip()
    assert issue_tree_id.startswith("issue_tree_")

    result = runner.invoke(
        app,
        ["execution", "plan-pack", thesis_id, "--workspace", "lab", "--root", str(root)],
    )
    assert result.exit_code == 0
    plan_pack_id = result.stdout.strip()
    assert plan_pack_id.startswith("plan_pack_")

    result = runner.invoke(
        app,
        ["execution", "review", thesis_id, "--workspace", "lab", "--root", str(root)],
    )
    assert result.exit_code == 0
    review_id = result.stdout.strip()
    assert review_id.startswith("execution_review_")

    result = runner.invoke(
        app,
        ["export", "readme", thesis_id, "--workspace", "lab", "--root", str(root)],
    )
    assert result.exit_code == 0
    readme_export_id = result.stdout.strip()
    assert readme_export_id.startswith("public_readme_")

    result = runner.invoke(
        app,
        ["export", "publish-pack", thesis_id, "--workspace", "lab", "--root", str(root)],
    )
    assert result.exit_code == 0
    publish_pack_id = result.stdout.strip()
    assert publish_pack_id.startswith("publish_pack_")

    result = runner.invoke(
        app,
        ["execution", "roadmap", thesis_id, "--workspace", "lab", "--root", str(root)],
    )
    assert result.exit_code == 0
    roadmap_id = result.stdout.strip()
    assert roadmap_id.startswith("roadmap_")

    result = runner.invoke(
        app,
        ["portfolio", "lineage", thesis_id, "--workspace", "lab", "--root", str(root)],
    )
    assert result.exit_code == 0
    lineage_id = result.stdout.strip()
    assert lineage_id.startswith("lineage_")

    result = runner.invoke(
        app,
        ["portfolio", "themes", "--workspace", "lab", "--root", str(root)],
    )
    assert result.exit_code == 0
    themes_id = result.stdout.strip()
    assert themes_id == "portfolio_themes_lab"

    result = runner.invoke(
        app,
        ["portfolio", "drift", "--workspace", "lab", "--root", str(root)],
    )
    assert result.exit_code == 0
    drift_id = result.stdout.strip()
    assert drift_id == "portfolio_drift_lab"

    result = runner.invoke(
        app,
        ["evidence", "audit", thesis_id, "--workspace", "lab", "--root", str(root)],
    )
    assert result.exit_code == 0
    audit_id = result.stdout.strip()
    assert audit_id.startswith("audit_")

    result = runner.invoke(
        app,
        ["portfolio", "review", "--workspace", "lab", "--root", str(root)],
    )
    assert result.exit_code == 0
    portfolio_review_id = result.stdout.strip()
    assert portfolio_review_id == "portfolio_review_lab"

    result = runner.invoke(
        app,
        ["portfolio", "rebalance", "--workspace", "lab", "--root", str(root)],
    )
    assert result.exit_code == 0
    rebalance_id = result.stdout.strip()
    assert rebalance_id == "portfolio_rebalance_lab"

    result = runner.invoke(
        app,
        ["portfolio", "map", "--workspace", "lab", "--root", str(root)],
    )
    assert result.exit_code == 0
    assert result.stdout.strip() == "portfolio_map_lab"

    workspace_dir = root / "lab"
    assert (workspace_dir / ".signalforge" / "workspace.json").exists()
    assert (workspace_dir / "artifacts" / "sources" / f"{source_ids[0]}.md").exists()
    assert (workspace_dir / "artifacts" / "insights" / f"{insight_id}.json").exists()
    assert (workspace_dir / "artifacts" / "insights" / f"{comparison_id}.md").exists()
    assert (workspace_dir / "artifacts" / "insights" / f"{contradiction_id}.json").exists()
    assert (workspace_dir / "artifacts" / "opportunities" / f"{whitespace_opp_id}.json").exists()
    assert (workspace_dir / "artifacts" / "opportunities" / "opp_signal-graph-engine.json").exists()
    assert (workspace_dir / "artifacts" / "theses" / f"{thesis_id}.md").exists()
    assert (workspace_dir / "artifacts" / "decisions" / f"{decision_id}.json").exists()
    assert (workspace_dir / "artifacts" / "experiments" / f"{brief_id}.md").exists()
    assert (workspace_dir / "artifacts" / "experiments" / f"{issue_tree_id}.json").exists()
    assert (workspace_dir / "artifacts" / "experiments" / f"{plan_pack_id}.json").exists()
    assert (workspace_dir / "artifacts" / "experiments" / f"{review_id}.md").exists()
    assert (workspace_dir / "artifacts" / "exports" / f"{readme_export_id}.md").exists()
    assert (workspace_dir / "artifacts" / "exports" / f"{publish_pack_id}.json").exists()
    assert (workspace_dir / "artifacts" / "experiments" / f"{roadmap_id}.md").exists()
    assert (workspace_dir / "artifacts" / "portfolio" / f"{lineage_id}.json").exists()
    assert (workspace_dir / "artifacts" / "portfolio" / f"{themes_id}.json").exists()
    assert (workspace_dir / "artifacts" / "portfolio" / f"{drift_id}.md").exists()
    assert (workspace_dir / "artifacts" / "portfolio" / f"{audit_id}.json").exists()
    assert (workspace_dir / "artifacts" / "portfolio" / f"{portfolio_review_id}.md").exists()
    assert (workspace_dir / "artifacts" / "portfolio" / f"{rebalance_id}.json").exists()
    assert (workspace_dir / "artifacts" / "portfolio" / "portfolio_map_lab.md").exists()

    source_payload = json.loads(
        (workspace_dir / "artifacts" / "sources" / f"{source_ids[0]}.json").read_text(encoding="utf-8")
    )
    assert source_payload["fingerprint"].startswith("sha256:")
    assert len(source_payload["tags"]) >= 1
    assert len(source_payload["signals"]) >= 1
    assert source_payload["strategic_summary"]
    assert source_payload["metadata"]["github_owner"] == "example"
    assert source_payload["metadata"]["language"] == "Python"
    assert "high-traction" in source_payload["signals"]
    assert source_payload["freshness_score"] >= 0.9
    assert "implementation-surface" in source_payload["domain_cues"]
    assert len(source_payload["capability_hints"]) >= 1

    article_payload = json.loads(
        (workspace_dir / "artifacts" / "sources" / f"{source_ids[1]}.json").read_text(encoding="utf-8")
    )
    assert article_payload["metadata"]["hostname"] == "example.com"
    assert "article-signal" in article_payload["signals"]
    assert article_payload["freshness_score"] == 0.72
    assert "market-framing" in article_payload["domain_cues"]

    paper_payload = json.loads(
        (workspace_dir / "artifacts" / "sources" / f"{source_ids[2]}.json").read_text(encoding="utf-8")
    )
    assert paper_payload["metadata"]["paper_source"] == "arxiv"
    assert paper_payload["author"] == "Jane Doe, John Roe"
    assert "paper-signal" in paper_payload["signals"]
    assert paper_payload["freshness_score"] == 0.82
    assert "research-literature" in paper_payload["domain_cues"]

    comparison_payload = json.loads(
        (workspace_dir / "artifacts" / "insights" / f"{comparison_id}.json").read_text(encoding="utf-8")
    )
    assert "shared_capabilities" in comparison_payload
    assert "differentiation_zones" in comparison_payload
    assert "freshness_profile" in comparison_payload
    assert "domain_cues" in comparison_payload
    assert "capability_hints" in comparison_payload

    contradiction_payload = json.loads(
        (workspace_dir / "artifacts" / "insights" / f"{contradiction_id}.json").read_text(encoding="utf-8")
    )
    assert "severity" in contradiction_payload
    assert "contradictions" in contradiction_payload

    thesis_payload = json.loads(
        (workspace_dir / "artifacts" / "theses" / f"{thesis_id}.json").read_text(encoding="utf-8")
    )
    assert thesis_payload["name"] == "Signal Graph Engine"
    assert thesis_payload["opportunity_id"] == "opp_signal-graph-engine"
    assert "comparison" in thesis_payload
    assert "contradictions" in thesis_payload
    assert "whitespace" in thesis_payload

    brief_payload = json.loads(
        (workspace_dir / "artifacts" / "experiments" / f"{brief_id}.json").read_text(encoding="utf-8")
    )
    assert brief_payload["thesis_id"] == thesis_id
    assert "contradictions" in brief_payload

    issue_tree_payload = json.loads(
        (workspace_dir / "artifacts" / "experiments" / f"{issue_tree_id}.json").read_text(encoding="utf-8")
    )
    assert len(issue_tree_payload["issues"]) == 5
    assert issue_tree_payload["issues"][1]["depends_on"] == ["SF-1"]
    assert "risk_flags" in issue_tree_payload["issues"][0]
    assert "acceptance_criteria" in issue_tree_payload["issues"][0]
    assert "verification_commands" in issue_tree_payload["issues"][0]
    assert "expected_outputs" in issue_tree_payload["issues"][0]
    assert "exit_conditions" in issue_tree_payload["issues"][0]
    assert "blockers" in issue_tree_payload["issues"][0]

    plan_pack_payload = json.loads(
        (workspace_dir / "artifacts" / "experiments" / f"{plan_pack_id}.json").read_text(encoding="utf-8")
    )
    assert plan_pack_payload["issue_count"] == 5

    review_payload = json.loads(
        (workspace_dir / "artifacts" / "experiments" / f"{review_id}.json").read_text(encoding="utf-8")
    )
    assert review_payload["readiness"] in {"gated", "clear"}
    assert "high_risk_work_items" in review_payload

    readme_export_payload = json.loads(
        (workspace_dir / "artifacts" / "exports" / f"{readme_export_id}.json").read_text(encoding="utf-8")
    )
    assert thesis_id == readme_export_payload["thesis_id"]
    assert "architecture_snippet" in readme_export_payload
    assert "launch_snippets" in readme_export_payload
    assert "example_artifact_snippet" in readme_export_payload

    publish_pack_payload = json.loads(
        (workspace_dir / "artifacts" / "exports" / f"{publish_pack_id}.json").read_text(encoding="utf-8")
    )
    assert publish_pack_payload["readme_export_id"] == readme_export_id
    assert publish_pack_payload["plan_pack_id"] == plan_pack_id
    assert "launch_snippets" in publish_pack_payload
    assert "architecture_snippet" in publish_pack_payload

    roadmap_payload = json.loads(
        (workspace_dir / "artifacts" / "experiments" / f"{roadmap_id}.json").read_text(encoding="utf-8")
    )
    assert len(roadmap_payload["roadmap"]) == 4

    decision_payload = json.loads(
        (workspace_dir / "artifacts" / "decisions" / f"{decision_id}.json").read_text(encoding="utf-8")
    )
    assert decision_payload["decision"] == "build"
    assert decision_payload["review_after"] == "2026-05-20"
    assert "decision_intelligence" in decision_payload
    assert decision_payload["decision_intelligence"]["confidence_after"] >= decision_payload["decision_intelligence"]["confidence_before"]

    themes_payload = json.loads(
        (workspace_dir / "artifacts" / "portfolio" / f"{themes_id}.json").read_text(encoding="utf-8")
    )
    assert "dominant_themes" in themes_payload
    assert "theme_concentration" in themes_payload
    assert "theme_hhi" in themes_payload
    assert "clusters" in themes_payload
    assert "whitespace_themes" in themes_payload
    assert "merge_candidates" in themes_payload
    assert "pairwise_overlaps" in themes_payload
    assert "diversification_targets" in themes_payload

    drift_payload = json.loads(
        (workspace_dir / "artifacts" / "portfolio" / f"{drift_id}.json").read_text(encoding="utf-8")
    )
    assert len(drift_payload["items"]) >= 1

    audit_payload = json.loads(
        (workspace_dir / "artifacts" / "portfolio" / f"{audit_id}.json").read_text(encoding="utf-8")
    )
    assert audit_payload["target_id"] == thesis_id
    assert audit_payload["bundle_health"] in {"strong", "watch", "fragile", "expired"}
    assert "source_checks" in audit_payload
    assert "provenance_score" in audit_payload
    assert "source_diversity_score" in audit_payload
    assert "review_after" in audit_payload
    assert "hard_triggers" in audit_payload
    assert "soft_triggers" in audit_payload
    assert "recommended_action" in audit_payload

    portfolio_review_payload = json.loads(
        (workspace_dir / "artifacts" / "portfolio" / f"{portfolio_review_id}.json").read_text(encoding="utf-8")
    )
    assert portfolio_review_payload["summary"]["thesis_count"] >= 1
    assert len(portfolio_review_payload["lane_assignments"]) >= 1
    assert "drift_alerts" in portfolio_review_payload
    assert "execution_gaps" in portfolio_review_payload
    assert "actions" in portfolio_review_payload
    assert "theme_intelligence" in portfolio_review_payload
    assert "merge_opportunities" in portfolio_review_payload
    assert "diversification_targets" in portfolio_review_payload

    rebalance_payload = json.loads(
        (workspace_dir / "artifacts" / "portfolio" / f"{rebalance_id}.json").read_text(encoding="utf-8")
    )
    assert len(rebalance_payload["attention_moves"]) >= 1
    assert "priority_order" in rebalance_payload
    assert "review_priorities" in rebalance_payload
    assert "merge_suggestions" in rebalance_payload
    assert "concentration_moves" in rebalance_payload
    assert "diversification_targets" in rebalance_payload


def test_evidence_audit_tracks_provenance_and_review_window() -> None:
    audit = audit_evidence_bundle(
        thesis_payload={
            "id": "thesis_signalforge-credibility",
            "contradictions": {"contradiction_count": 1, "severity": "medium"},
            "whitespace": {"category_pressure": "rising"},
        },
        sources=[
            {
                "id": "src_repo_signalforge",
                "type": "repo",
                "uri": "https://github.com/example/signalforge",
                "author": "example",
                "freshness_score": 0.94,
                "captured_at": "2026-04-03T00:00:00Z",
                "metadata": {"github_owner": "example", "github_repo": "signalforge", "stars": "12000", "updated_at": "2026-04-02T00:00:00Z"},
                "signals": ["high-traction", "decision-grade"],
                "domain_cues": ["builder-tooling", "research-literature"],
                "capability_hints": ["agent-coordination", "memory-layer"],
            },
            {
                "id": "src_article_market",
                "type": "article",
                "uri": "https://example.com/article",
                "freshness_score": 0.72,
                "captured_at": "2026-04-01T00:00:00Z",
                "metadata": {"hostname": "example.com", "last_modified": "2026-03-29T00:00:00Z"},
                "signals": ["article-signal", "decision-grade"],
                "domain_cues": ["builder-tooling", "market-framing"],
                "capability_hints": ["agent-coordination", "launch-assets"],
            },
            {
                "id": "src_note_founder",
                "type": "note",
                "freshness_score": 0.58,
                "captured_at": "2026-03-10T00:00:00Z",
                "metadata": {"captured_from": "local"},
                "signals": ["founder-note", "decision-grade"],
                "domain_cues": ["builder-tooling", "founder-judgment"],
                "capability_hints": ["agent-coordination", "execution-planning"],
            },
        ],
        decisions=[{"id": "decision_build_signalforge"}],
        execution_artifacts=[{"id": "brief_1"}, {"id": "roadmap_1"}, {"id": "review_1"}],
    )

    assert audit["provenance_score"] >= 0.7
    assert audit["source_diversity_score"] >= 0.75
    assert audit["convergence_score"] >= 0.45
    assert audit["convergence_state"] in {"moderate", "strong"}
    assert "builder-tooling" in audit["shared_support_features"]
    assert audit["average_source_age_days"] is not None
    assert datetime.fromisoformat(audit["review_after"])
    assert any(item["provenance_quality"] == "verified-repository" for item in audit["source_checks"])
    assert all("credibility_score" in item for item in audit["source_checks"])
    assert all("support_features" in item for item in audit["source_checks"])
    assert any(item["days_since_capture"] is not None for item in audit["source_checks"])


def test_infer_freshness_score_accepts_http_last_modified_dates() -> None:
    freshness = infer_freshness_score(
        "article",
        {"hostname": "example.com", "last_modified": "Wed, 01 Apr 2026 12:00:00 GMT"},
    )

    assert freshness >= 0.72


def test_build_theme_intelligence_surfaces_clusters_and_risk() -> None:
    intelligence = build_theme_intelligence(
        [
            {
                "id": "thesis_signalforge",
                "name": "SignalForge",
                "comparison": {
                    "domain_cues": ["builder-tooling", "research-literature"],
                    "capability_hints": ["agent-coordination", "memory-layer"],
                },
            },
            {
                "id": "thesis_portfolio_ops",
                "name": "Portfolio Ops",
                "comparison": {
                    "domain_cues": ["builder-tooling"],
                    "capability_hints": ["agent-coordination", "workflow-orchestration"],
                },
            },
            {
                "id": "thesis_launch_surface",
                "name": "Launch Surface",
                "comparison": {
                    "domain_cues": ["public-narrative"],
                    "capability_hints": ["launch-assets"],
                },
            },
        ]
    )

    assert intelligence["theme_concentration"] >= 0.67
    assert intelligence["concentration_state"] in {"tilted", "concentrated"}
    assert intelligence["clusters"][0]["cluster_size"] >= 2
    assert any(risk["theme"] == "builder-tooling" for risk in intelligence["concentration_risks"])
    assert "public-narrative" in intelligence["whitespace_themes"]
    assert intelligence["pairwise_overlaps"][0]["merge_uplift"] >= 0.4
    assert any(candidate["pair"] == ["thesis_portfolio_ops", "thesis_signalforge"] or candidate["pair"] == ["thesis_signalforge", "thesis_portfolio_ops"] for candidate in intelligence["merge_candidates"])
    assert any(target["theme"] == "public-narrative" for target in intelligence["diversification_targets"])


def test_portfolio_review_promotes_merge_and_diversification_intelligence() -> None:
    theses = [
        {
            "id": "thesis_signalforge",
            "name": "SignalForge",
            "comparison": {
                "domain_cues": ["builder-tooling", "research-literature"],
                "capability_hints": ["agent-coordination", "memory-layer"],
                "overlap_strength": 0.22,
            },
            "whitespace": {"whitespace_score": 8.6},
            "opportunity": {"scores": {"strategic_leverage": 8.7}},
        },
        {
            "id": "thesis_portfolio_ops",
            "name": "Portfolio Ops",
            "comparison": {
                "domain_cues": ["builder-tooling"],
                "capability_hints": ["agent-coordination", "workflow-orchestration"],
                "overlap_strength": 0.21,
            },
            "whitespace": {"whitespace_score": 8.1},
            "opportunity": {"scores": {"strategic_leverage": 8.2}},
        },
        {
            "id": "thesis_launch_surface",
            "name": "Launch Surface",
            "comparison": {
                "domain_cues": ["public-narrative"],
                "capability_hints": ["launch-assets"],
                "overlap_strength": 0.12,
            },
            "whitespace": {"whitespace_score": 7.9},
            "opportunity": {"scores": {"strategic_leverage": 7.8}},
        },
    ]
    audits = {
        thesis["id"]: {
            "bundle_health": "watch",
            "coverage_score": 0.82,
            "freshness_score": 0.86,
            "contradiction_score": 0.08,
            "evidence_gaps": [],
            "recommended_action": "maintain_commitment",
        }
        for thesis in theses
    }
    decisions_by_thesis = {thesis["id"]: [{"id": f"decision_{thesis['id']}", "decision": "build"}] for thesis in theses}
    execution_by_thesis = {thesis["id"]: [{"id": f"brief_{thesis['id']}"}, {"id": f"roadmap_{thesis['id']}"}] for thesis in theses}

    review = build_portfolio_review(theses, audits, decisions_by_thesis, execution_by_thesis)
    rebalance = build_portfolio_rebalance(review)

    assert review["summary"]["merge_opportunity_count"] >= 1
    assert review["theme_intelligence"]["concentration_state"] in {"tilted", "concentrated"}
    assert any(item["drift_type"] == "portfolio_overlap" for item in review["drift_alerts"])
    assert any(item["action"] == "evaluate_merge_pair" for item in review["actions"])
    assert any(item["theme"] == "public-narrative" for item in review["diversification_targets"])
    assert rebalance["merge_suggestions"]
    assert rebalance["concentration_moves"]
    assert any(item["theme"] == "public-narrative" for item in rebalance["diversification_targets"])
