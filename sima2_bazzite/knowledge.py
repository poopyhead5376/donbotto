from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SkillAttempt:
    feature: str
    action: str
    success: bool
    notes: str


class KnowledgeStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature TEXT NOT NULL,
                action TEXT NOT NULL,
                success INTEGER NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_attempts_feature ON attempts(feature);
            """
        )
        self.conn.commit()

    def record_attempt(self, attempt: SkillAttempt) -> None:
        self.conn.execute(
            "INSERT INTO attempts(feature, action, success, notes) VALUES (?, ?, ?, ?)",
            (attempt.feature, attempt.action, int(attempt.success), attempt.notes),
        )
        self.conn.commit()

    def success_rate(self, feature: str) -> float:
        row = self.conn.execute(
            "SELECT COALESCE(AVG(success), 0.0) FROM attempts WHERE feature = ?",
            (feature,),
        ).fetchone()
        return float(row[0] if row else 0.0)

    def best_action(self, feature: str) -> str | None:
        row = self.conn.execute(
            """
            SELECT action, AVG(success) as rate, COUNT(*) as n
            FROM attempts
            WHERE feature = ?
            GROUP BY action
            ORDER BY rate DESC, n DESC
            LIMIT 1
            """,
            (feature,),
        ).fetchone()
        return str(row[0]) if row else None

    def close(self) -> None:
        self.conn.close()
