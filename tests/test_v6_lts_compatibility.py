"""Frozen v6.x LTS SDK and Extension compatibility contracts."""

from __future__ import annotations

from pathlib import Path

from manga_director.production import (
    ExtensionFrameworkDTO,
    SDKCapabilityDTO,
    V60CreativeProductionPlatformCoreService,
)

ROOT = Path(__file__).resolve().parents[1]


def _enum_values(model: type[SDKCapabilityDTO | ExtensionFrameworkDTO], field: str) -> tuple[str, ...]:
    values = model.model_json_schema()["properties"][field]["enum"]
    return tuple(values)


def test_lts_sdk_compatibility_matrix_matches_the_frozen_descriptor_contract() -> None:
    surfaces = _enum_values(SDKCapabilityDTO, "surface")
    labels = _enum_values(SDKCapabilityDTO, "compatibility")
    sdk = V60CreativeProductionPlatformCoreService().sdk_foundation(
        tuple(
            SDKCapabilityDTO(
                capability_id=f"sdk:{surface}",
                surface=surface,
                source_reference="manga_director",
                compatibility=labels[index % len(labels)],
            )
            for index, surface in enumerate(surfaces)
        )
    )

    document = (ROOT / "docs" / "SDK_COMPATIBILITY_MATRIX.md").read_text(encoding="utf-8")

    assert surfaces == ("python", "cli", "fastapi", "mcp", "web_ui")
    assert labels == ("v5_additive", "v6_foundation")
    assert sdk.compatible is True
    assert sdk.surface_count == len(surfaces)
    assert sdk.sdk_published is False
    assert sdk.public_api_changed is False
    assert "`SDKCapabilityDTO` is a read-only compatibility descriptor" in document
    for surface in ("Python", "CLI", "FastAPI / REST", "MCP", "Web UI"):
        assert f"| {surface} |" in document


def test_lts_extension_compatibility_matrix_matches_the_frozen_descriptor_contract() -> None:
    extension_types = _enum_values(ExtensionFrameworkDTO, "extension_type")
    labels = _enum_values(ExtensionFrameworkDTO, "compatibility")
    extensions = V60CreativeProductionPlatformCoreService().extension_framework(
        tuple(
            ExtensionFrameworkDTO(
                extension_id=f"extension:{extension_type}",
                name=extension_type,
                extension_type=extension_type,
                compatibility=labels[index % len(labels)],
            )
            for index, extension_type in enumerate(extension_types)
        )
    )

    document = (ROOT / "docs" / "EXTENSION_COMPATIBILITY_MATRIX.md").read_text(
        encoding="utf-8"
    )

    assert extension_types == ("sdk", "automation", "knowledge", "collaboration", "analytics")
    assert labels == ("v5_additive", "v6_foundation")
    assert extensions.compatible is True
    assert tuple(item.extension_type for item in extensions.extensions) == tuple(
        sorted(extension_types)
    )
    assert all(item.extension_registered is False for item in extensions.extensions)
    assert all(item.extension_loaded is False for item in extensions.extensions)
    assert all(item.extension_executed is False for item in extensions.extensions)
    assert "`v5_additive`, `v6_foundation`" in document
    assert "compatibility evidence only" in document
    for extension_type in ("SDK", "Automation", "Knowledge", "Collaboration", "Analytics"):
        assert f"| {extension_type} |" in document
