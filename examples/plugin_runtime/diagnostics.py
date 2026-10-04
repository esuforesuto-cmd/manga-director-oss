"""Inspect cached Plugin Runtime state without loading a plugin."""

import logging
from pathlib import Path

from manga_director.plugins import PluginManager

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

manager = PluginManager(Path("plugins"))
manager.discover()
LOGGER.info("%s", manager.diagnostics())
