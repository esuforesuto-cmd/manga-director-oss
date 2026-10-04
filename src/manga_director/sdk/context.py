"""Stable context made available to third-party extensions."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from manga_director.events.bus import EventBus
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.engine import WorkflowEngine


@dataclass(frozen=True)
class ExtensionContext:
    """Core services exposed through the supported Extension SDK boundary."""

    configuration: dict[str, Any]
    logger: logging.Logger
    event_bus: EventBus
    factories: dict[str, Any]
    workflow_engine: WorkflowEngine
    repository: ProjectRepository
