"""Build a transport-neutral health DTO without a web framework."""

import logging

from manga_director.observability import HealthMonitor

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

dashboard = HealthMonitor({"repository": lambda: True, "plugin_runtime": lambda: True}).dashboard()
LOGGER.info("%s", dashboard.model_dump(mode="json"))
