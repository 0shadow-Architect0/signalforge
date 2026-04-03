from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import re


ARTIFACT_DIRS = {
    "source": "sources",
    "insight": "insights",
    "opportunity": "opportunities",
    "thesis": "theses",
    "decision": "decisions",
    "experiment": "experiments",
    "portfolio": "portfolio",
    "export": "exports",
}


@dataclass(frozen=True)
class WorkspacePaths:
    name: str
    root: Path

    @property
    def workspace_dir(self) -> Path:
        return self.root / self.name

    @property
    def state_dir(self) -> Path:
        return self.workspace_dir / ".signalforge"

    @property
    def artifacts_dir(self) -> Path:
        return self.workspace_dir / "artifacts"

    def artifact_dir(self, artifact_type: str) -> Path:
        return self.artifacts_dir / ARTIFACT_DIRS[artifact_type]

    def ensure(self) -> None:
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        for directory in ARTIFACT_DIRS.values():
            (self.artifacts_dir / directory).mkdir(parents=True, exist_ok=True)

    def manifest_path(self) -> Path:
        return self.state_dir / "workspace.json"

    def write_manifest(self) -> None:
        payload = {
            "name": self.name,
            "workspace_dir": str(self.workspace_dir),
            "created_at": utc_now(),
            "artifact_directories": ARTIFACT_DIRS,
        }
        self.manifest_path().write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_workspace(name: str, root: Path) -> WorkspacePaths:
    workspace = WorkspacePaths(name=name, root=root)
    workspace.ensure()
    if not workspace.manifest_path().exists():
        workspace.write_manifest()
    return workspace


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "item"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def frontmatter(payload: dict[str, object]) -> str:
    lines = ["---"]
    for key, value in payload.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        elif value is None:
            lines.append(f"{key}: null")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)
