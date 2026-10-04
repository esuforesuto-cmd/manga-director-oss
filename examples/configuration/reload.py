"""Load a config repeatedly; it is revalidated only after file/env changes."""

import logging
from pathlib import Path

from manga_director.cli.config import configuration_diagnostics, load_config

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

config_path = Path("config.yaml")
config = load_config(config_path)
assert load_config(config_path) is config
LOGGER.info("%s", configuration_diagnostics(config_path))
