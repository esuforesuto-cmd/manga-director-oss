"""Contracts for the v4.4 Enterprise Creative Platform design cycle."""

from __future__ import annotations

import re
from pathlib import Path

import manga_director

ROOT = Path(__file__).resolve().parents[1]


def test_v4_4_planning_assets_keep_the_v4_3_release_baseline() -> None:
    documents = (
        "docs/VISION_V4_4.md",
        "docs/ARCHITECTURE_V4_4.md",
        "docs/ENTERPRISE_PLATFORM.md",
        "docs/COLLABORATION.md",
        "docs/PORTFOLIO_MANAGEMENT.md",
        "docs/EXTENSION_ECOSYSTEM.md",
        "docs/ROADMAP_V4_4.md",
        "docs/MIGRATION_V4_4.md",
        "docs/V4_4_DEVELOPMENT_PLANNING_REPORT.md",
    )

    assert manga_director.__version__ == "6.0.0"
    assert all((ROOT / document).is_file() for document in documents)

    vision = (ROOT / "docs/VISION_V4_4.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs/ARCHITECTURE_V4_4.md").read_text(encoding="utf-8")
    extension = (ROOT / "docs/EXTENSION_ECOSYSTEM.md").read_text(encoding="utf-8")

    assert "does not authorize autonomous AI" in vision
    assert "StateMachine" in architecture
    assert "no authority to" in architecture
    assert "cannot load an extension" in extension


def test_v4_4_planning_links_quality_gates_and_debt_are_resolvable() -> None:
    documents = (
        ROOT / "docs/VISION_V4_4.md",
        ROOT / "docs/ARCHITECTURE_V4_4.md",
        ROOT / "docs/ENTERPRISE_PLATFORM.md",
        ROOT / "docs/COLLABORATION.md",
        ROOT / "docs/PORTFOLIO_MANAGEMENT.md",
        ROOT / "docs/EXTENSION_ECOSYSTEM.md",
        ROOT / "docs/ROADMAP_V4_4.md",
        ROOT / "docs/MIGRATION_V4_4.md",
        ROOT / "docs/V4_4_DEVELOPMENT_PLANNING_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    for document in documents:
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", document.read_text(encoding="utf-8")):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            assert (document.parent / link).exists(), f"{document}: broken link to {link}"

    for gate in (
        "Enterprise Workspace Design Validation",
        "Collaboration Design Validation",
        "Portfolio Design Validation",
        "Marketplace Design Validation",
        "Extension Ecosystem Design Validation",
    ):
        assert gate in gates
    for category in (
        "Enterprise Workspace",
        "Team Collaboration",
        "Portfolio Management",
        "Workflow Marketplace",
        "Extension Ecosystem",
    ):
        assert category in debt
