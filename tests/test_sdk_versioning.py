"""Compatibility checks for the supported Extension SDK version boundary."""

from __future__ import annotations

import pytest

from manga_director import __version__
from manga_director.domain.exceptions import ValidationError
from manga_director.sdk.manifest import ExtensionManifest, ExtensionValidator


def _manifest(minimum_core_version: str) -> ExtensionManifest:
    return ExtensionManifest(
        id="release-contract",
        name="Release Contract",
        version="1.0.0",
        author="tests",
        license="MIT",
        description="Compatibility fixture",
        entry_point="manga_director.sdk.extension:Extension",
        minimum_core_version=minimum_core_version,
    )


def test_extension_validator_defaults_to_the_installed_core_version() -> None:
    validated = ExtensionValidator().validate(_manifest(__version__))

    assert validated.minimum_core_version == __version__


def test_extension_validator_rejects_a_newer_core_requirement() -> None:
    with pytest.raises(ValidationError, match="not compatible"):
        ExtensionValidator().validate(_manifest("9999.0.0"))
