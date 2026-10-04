"""Reuse a validator safely when validating the same extension manifest."""

import logging
from pathlib import Path

from manga_director.sdk import ExtensionValidator

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

validator = ExtensionValidator()
manifest_path = Path(__file__).with_name("manifest.yaml")
manifest = validator.load(manifest_path)
assert validator.load(manifest_path) is manifest
LOGGER.info("%s", validator.diagnostics())
