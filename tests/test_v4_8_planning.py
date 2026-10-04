"""Contracts for the v4.8 Creative Operating System planning cycle."""

from __future__ import annotations

import re
from pathlib import Path

import manga_director

ROOT = Path(__file__).resolve().parents[1]


def test_v4_8_planning_assets_keep_the_v4_7_release_baseline() -> None:
    documents = (
        "docs/VISION_V4_8.md",
        "docs/ARCHITECTURE_V4_8.md",
        "docs/UNIFIED_PLATFORM.md",
        "docs/MODULAR_RUNTIME.md",
        "docs/LIFECYCLE_MANAGEMENT.md",
        "docs/OPERATIONAL_INTELLIGENCE.md",
        "docs/ROADMAP_V4_8.md",
        "docs/MIGRATION_V4_8.md",
        "docs/V4_8_DEVELOPMENT_PLANNING_REPORT.md",
    )

    assert manga_director.__version__ == "6.0.0"
    assert all((ROOT / document).is_file() for document in documents)

    vision = (ROOT / "docs/VISION_V4_8.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs/ARCHITECTURE_V4_8.md").read_text(encoding="utf-8")
    lifecycle = (ROOT / "docs/LIFECYCLE_MANAGEMENT.md").read_text(encoding="utf-8")

    assert "design-only" in vision
    assert "StateMachine" in architecture
    assert "exactly-one-Page" in architecture
    assert "completed quality review" in lifecycle


def test_v4_8_planning_links_quality_gates_and_debt_are_resolvable() -> None:
    documents = (
        ROOT / "docs/VISION_V4_8.md",
        ROOT / "docs/ARCHITECTURE_V4_8.md",
        ROOT / "docs/UNIFIED_PLATFORM.md",
        ROOT / "docs/MODULAR_RUNTIME.md",
        ROOT / "docs/LIFECYCLE_MANAGEMENT.md",
        ROOT / "docs/OPERATIONAL_INTELLIGENCE.md",
        ROOT / "docs/ROADMAP_V4_8.md",
        ROOT / "docs/MIGRATION_V4_8.md",
        ROOT / "docs/V4_8_DEVELOPMENT_PLANNING_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    for document in documents:
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", document.read_text(encoding="utf-8")):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            assert (document.parent / link).exists(), f"{document}: broken link to {link}"

    for gate in (
        "Unified Platform Design Validation",
        "Modular Runtime Design Validation",
        "Unified API Surface Validation",
        "Operational Intelligence Design Validation",
        "Lifecycle Management Design Validation",
        "Backward Compatibility Validation",
    ):
        assert gate in gates
    for category in (
        "v4.8 Planning",
        "Unified Creative Platform",
        "Modular Runtime",
        "Operational Intelligence",
        "Lifecycle Management",
    ):
        assert category in debt
