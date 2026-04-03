"""Persistence Layer - SQLite backend for SignalForge state."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SignalForgeDB:
    """SQLite persistence for snapshots, reports, and convergence events."""
    
    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            db_path = Path.home() / ".signalforge" / "signalforge.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn
    
    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thesis_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                payload TEXT NOT NULL,
                composite_score REAL DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace TEXT DEFAULT 'default',
                portfolio_health TEXT DEFAULT 'unknown',
                top_priority TEXT,
                thesis_count INTEGER DEFAULT 0,
                payload TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS convergence_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thesis_ids TEXT NOT NULL,
                convergence_score REAL DEFAULT 0,
                convergence_type TEXT DEFAULT 'unknown',
                signal_strength TEXT DEFAULT 'weak',
                opportunity_space TEXT,
                payload TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_snapshots_thesis ON snapshots(thesis_id);
            CREATE INDEX IF NOT EXISTS idx_snapshots_ts ON snapshots(timestamp);
            CREATE INDEX IF NOT EXISTS idx_reports_workspace ON reports(workspace);
            CREATE INDEX IF NOT EXISTS idx_convergence_ts ON convergence_events(created_at);
        """)
        conn.commit()
    
    # ── Snapshots ──
    
    def save_snapshot(self, thesis_id: str, payload: dict, composite_score: float = 0.0) -> int:
        conn = self._get_conn()
        cur = conn.execute(
            "INSERT INTO snapshots (thesis_id, timestamp, payload, composite_score) VALUES (?, ?, ?, ?)",
            (thesis_id, datetime.now(timezone.utc).isoformat(), json.dumps(payload), composite_score),
        )
        conn.commit()
        return cur.lastrowid
    
    def get_snapshots(self, thesis_id: str, limit: int = 100) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM snapshots WHERE thesis_id = ? ORDER BY timestamp DESC LIMIT ?",
            (thesis_id, limit),
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["payload"] = json.loads(d["payload"])
            results.append(d)
        return results
    
    def get_latest_snapshot(self, thesis_id: str) -> dict | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM snapshots WHERE thesis_id = ? ORDER BY timestamp DESC LIMIT 1",
            (thesis_id,),
        ).fetchone()
        if row:
            result = dict(row)
            if result.get("payload"):
                result["payload"] = json.loads(result["payload"])
            return result
        return None
    
    def get_all_thesis_ids(self) -> list[str]:
        conn = self._get_conn()
        rows = conn.execute("SELECT DISTINCT thesis_id FROM snapshots").fetchall()
        return [r["thesis_id"] for r in rows]
    
    def snapshot_count(self, thesis_id: str | None = None) -> int:
        conn = self._get_conn()
        if thesis_id:
            row = conn.execute("SELECT COUNT(*) as cnt FROM snapshots WHERE thesis_id = ?", (thesis_id,)).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) as cnt FROM snapshots").fetchone()
        return row["cnt"] if row else 0
    
    # ── Reports ──
    
    def save_report(self, workspace: str, report_dict: dict) -> int:
        conn = self._get_conn()
        cur = conn.execute(
            "INSERT INTO reports (workspace, portfolio_health, top_priority, thesis_count, payload) VALUES (?, ?, ?, ?, ?)",
            (
                workspace,
                report_dict.get("portfolio_health", "unknown"),
                report_dict.get("top_priority"),
                report_dict.get("thesis_count", 0),
                json.dumps(report_dict, default=str),
            ),
        )
        conn.commit()
        return cur.lastrowid
    
    def get_latest_report(self, workspace: str = "default") -> dict | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM reports WHERE workspace = ? ORDER BY created_at DESC LIMIT 1",
            (workspace,),
        ).fetchone()
        if row:
            result = dict(row)
            if result.get("payload"):
                result["payload"] = json.loads(result["payload"])
            return result
        return None
    
    def get_reports(self, workspace: str = "default", limit: int = 20) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM reports WHERE workspace = ? ORDER BY created_at DESC LIMIT ?",
            (workspace, limit),
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            if d.get("payload"):
                d["payload"] = json.loads(d["payload"])
            results.append(d)
        return results
    
    # ── Convergence Events ──
    
    def save_convergence_event(self, convergence_dict: dict) -> int:
        conn = self._get_conn()
        cur = conn.execute(
            "INSERT INTO convergence_events (thesis_ids, convergence_score, convergence_type, signal_strength, opportunity_space, payload) VALUES (?, ?, ?, ?, ?, ?)",
            (
                json.dumps(convergence_dict.get("thesis_ids", [])),
                convergence_dict.get("convergence_score", 0),
                convergence_dict.get("convergence_type", "unknown"),
                convergence_dict.get("signal_strength", "weak"),
                convergence_dict.get("opportunity_space", ""),
                json.dumps(convergence_dict, default=str),
            ),
        )
        conn.commit()
        return cur.lastrowid
    
    def get_convergence_history(self, limit: int = 20) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM convergence_events ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    
    # ── Cleanup ──
    
    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def delete_old_snapshots(self, keep_days: int = 90) -> int:
        conn = self._get_conn()
        cur = conn.execute(
            "DELETE FROM snapshots WHERE created_at < datetime('now', ?)",
            (f"-{keep_days} days",),
        )
        conn.commit()
        return cur.rowcount
