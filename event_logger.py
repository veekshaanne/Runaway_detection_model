
import json
import sqlite3
import time


class EventLogger:
    def __init__(self, db_path):
        self.db_path = db_path
        self._create_table()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _create_table(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS action_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    action_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    target TEXT,
                    arguments TEXT,
                    timestamp REAL NOT NULL,
                    result TEXT,
                    risk_score REAL NOT NULL,
                    decision TEXT NOT NULL,
                    reasons TEXT NOT NULL DEFAULT '[]',
                    token_count INTEGER NOT NULL DEFAULT 0,
                    latency_ms REAL NOT NULL DEFAULT 0.0
                )
                """
            )

            columns = {
                row[1]
                for row in conn.execute(
                    "PRAGMA table_info(action_events)"
                )
            }

            if "reasons" not in columns:
                conn.execute(
                    "ALTER TABLE action_events "
                    "ADD COLUMN reasons TEXT NOT NULL DEFAULT '[]'"
                )

            if "token_count" not in columns:
                conn.execute(
                    "ALTER TABLE action_events "
                    "ADD COLUMN token_count INTEGER NOT NULL DEFAULT 0"
                )

            if "latency_ms" not in columns:
                conn.execute(
                    "ALTER TABLE action_events "
                    "ADD COLUMN latency_ms REAL NOT NULL DEFAULT 0.0"
                )

    def log(self, action, result, risk_score, decision, reasons=None,
            token_count: int = 0, latency_ms: float = 0.0):
        if reasons is None:
            reasons = []

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO action_events
                (task_id, action_id, action_type, target, arguments,
                 timestamp, result, risk_score, decision, reasons,
                 token_count, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action.get("task_id", "task-1"),
                    action.get("action_id", 0),
                    action.get("action_type", "unknown"),
                    action.get("target", ""),
                    json.dumps(
                        action.get("arguments", {}), sort_keys=True
                    ),
                    time.time(),
                    json.dumps(result, sort_keys=True)
                    if result is not None else None,
                    float(risk_score),
                    decision,
                    json.dumps(reasons),
                    int(token_count),
                    float(latency_ms),
                ),
            )
