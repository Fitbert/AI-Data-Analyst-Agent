"""
Append-only audit log.

This scaffold writes JSONL to disk, which is enough to prove the pattern
end to end. Production should replace this with a real table/log
pipeline (e.g. a dedicated audit_log table with its own retention
policy, or shipped to a log aggregator) -- see architecture doc,
section 4.6. The important invariant to keep either way: log BEFORE
returning the response to the user, and never allow this write to fail
silently.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from config import settings


def log_query(*, question: str, sql: str, row_count: int, user: str | None, error: str | None = None) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user": user or "anonymous",
        "question": question,
        "sql": sql,
        "row_count": row_count,
        "error": error,
    }
    path = Path(settings.audit_log_path)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
