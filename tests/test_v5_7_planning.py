"""Contracts for the v5.7 Manga Production Platform planning cycle."""

from __future__ import annotations

from pathlib import Path

import manga_director

ROOT = Path(__file__).resolve().parents[1]


def test_v5_7_planning_preserves_the_v5_6_maintenance_baseline() -> None:
    documents = (
        "docs/VISION_V5_7.md",
        "docs/ARCHITECTURE_V5_7.md",
        "docs/ROADMAP_V5_7.md",
        "docs/PLATFORM_EVOLUTION.md",
        "docs/MIGRATION_V5_6_TO_V5_7.md",
    )

    assert manga_director.__version__ == "6.0.0"
    assert all((ROOT / document).is_file() for document in documents)


def test_v5_7_architecture_keeps_platform_services_read_only() -> None:
    architecture = " ".join(
        (ROOT / "docs/ARCHITECTURE_V5_7.md").read_text(encoding="utf-8").split()
    )

    assert "Application-layer composition" in architecture
    assert "StateMachine owns legal transitions" in architecture
    assert "exactly one Page" in architecture
    assert "cannot execute, advance, save, register, load, or publish" in architecture


def test_v5_7_migration_and_platform_boundaries_preserve_existing_owners() -> None:
    migration = (ROOT / "docs/MIGRATION_V5_6_TO_V5_7.md").read_text(encoding="utf-8")
    evolution = (ROOT / "docs/PLATFORM_EVOLUTION.md").read_text(encoding="utf-8")
    automation = (ROOT / "docs/AUTOMATION_FRAMEWORK.md").read_text(encoding="utf-8")
    plugins = (ROOT / "docs/PLUGIN_ECOSYSTEM.md").read_text(encoding="utf-8")

    assert "requires no installation action" in migration
    assert "repository-interface change" in migration
    assert "do not change repository interfaces" in evolution
    assert "introduces no dispatcher" in automation
    assert "sole capability source" in " ".join(plugins.split())
