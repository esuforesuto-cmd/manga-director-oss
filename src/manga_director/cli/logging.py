from __future__ import annotations

import logging

from manga_director.domain.exceptions import ConfigurationError

LOGGER = logging.getLogger(__name__)


def configure_logging(level_name: str) -> logging.Logger:
    try:
        level = getattr(logging, level_name.upper())
    except AttributeError as exc:
        raise ConfigurationError(f"Unsupported log level: {level_name}") from exc
    if not isinstance(level, int):
        raise ConfigurationError(f"Unsupported log level: {level_name}")
    logging.basicConfig(level=level, format="%(levelname)s %(name)s %(message)s", force=True)
    return LOGGER
