"""Render the same safe Runtime report as JSON and Markdown."""

import logging

from manga_director.observability import MetricsRegistry, RuntimeDiagnostics

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

report = RuntimeDiagnostics(MetricsRegistry()).report(configuration={"cache_entries": 0})
LOGGER.info("%s", report.to_json())
LOGGER.info("%s", report.to_markdown())
