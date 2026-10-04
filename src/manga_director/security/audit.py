"""In-memory audit log with explicit, caller-provided metadata."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class AuditLogger:
    """Collect security-relevant application actions for a single process."""

    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    def record(
        self,
        action: str,
        *,
        project_id: str | None = None,
        actor: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.entries.append(
            {
                "action": action,
                "project_id": project_id,
                "actor": actor,
                "metadata": metadata or {},
                "occurred_at": datetime.now(UTC).isoformat(),
            }
        )
