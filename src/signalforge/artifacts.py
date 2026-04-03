from __future__ import annotations

from pathlib import Path
import json

from .workspace import WorkspacePaths, frontmatter


def write_artifact(
    workspace: WorkspacePaths,
    artifact_type: str,
    artifact_id: str,
    markdown_title: str,
    markdown_body: str,
    payload: dict,
) -> tuple[Path, Path]:
    directory = workspace.artifact_dir(artifact_type)
    md_path = directory / f"{artifact_id}.md"
    json_path = directory / f"{artifact_id}.json"

    fm = frontmatter(
        {
            "id": artifact_id,
            "type": artifact_type,
            "workspace": workspace.name,
            "updated_at": payload.get("updated_at") or payload.get("captured_at") or payload.get("created_at"),
            "source_ids": payload.get("source_ids", []),
        }
    )
    md_content = f"{fm}\n\n# {markdown_title}\n\n{markdown_body.strip()}\n"
    md_path.write_text(md_content, encoding="utf-8")
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return md_path, json_path
