"""Create a passive Runtime diagnostic report from safe snapshots."""

import logging

from manga_director.events import MemoryEventBus
from manga_director.observability import MetricsRegistry, RuntimeDiagnostics

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

events = MemoryEventBus()
report = RuntimeDiagnostics(MetricsRegistry()).report(events=events.diagnostics())
LOGGER.info("%s", report.model_dump())
