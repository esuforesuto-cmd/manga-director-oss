"""Contracts for the v4.5 Creative Intelligence Ecosystem design cycle."""

from __future__ import annotations

import re
from pathlib import Path

import manga_director

ROOT = Path(__file__).resolve().parents[1]


def test_v4_5_planning_assets_keep_the_v4_4_release_baseline() -> None:
    documents = (
        "docs/VISION_V4_5.md",
        "docs/ARCHITECTURE_V4_5.md",
        "docs/CREATIVE_ECOSYSTEM.md",
        "docs/PLUGIN_ECOSYSTEM.md",
        "docs/KNOWLEDGE_EXCHANGE.md",
        "docs/FEDERATION_ARCHITECTURE.md",
        "docs/ROADMAP_V4_5.md",
        "docs/MIGRATION_V4_5.md",
        "docs/V4_5_DEVELOPMENT_PLANNING_REPORT.md",
    )

    assert manga_director.__version__ == "6.0.0"
    assert all((ROOT / document).is_file() for document in documents)

    vision = (ROOT / "docs/VISION_V4_5.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs/ARCHITECTURE_V4_5.md").read_text(encoding="utf-8")
    federation = (ROOT / "docs/FEDERATION_ARCHITECTURE.md").read_text(encoding="utf-8")

    assert "does not authorize autonomous AI" in vision
    assert "StateMachine" in architecture
    assert "no authority to" in architecture
    assert "does not implement a federation protocol" in federation


def test_v4_5_planning_links_quality_gates_and_debt_are_resolvable() -> None:
    documents = (
        ROOT / "docs/VISION_V4_5.md",
        ROOT / "docs/ARCHITECTURE_V4_5.md",
        ROOT / "docs/CREATIVE_ECOSYSTEM.md",
        ROOT / "docs/PLUGIN_ECOSYSTEM.md",
        ROOT / "docs/KNOWLEDGE_EXCHANGE.md",
        ROOT / "docs/FEDERATION_ARCHITECTURE.md",
        ROOT / "docs/ROADMAP_V4_5.md",
        ROOT / "docs/MIGRATION_V4_5.md",
        ROOT / "docs/V4_5_DEVELOPMENT_PLANNING_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    for document in documents:
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", document.read_text(encoding="utf-8")):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            assert (document.parent / link).exists(), f"{document}: broken link to {link}"

    for gate in (
        "Creative Service Platform Design Validation",
        "Plugin Ecosystem Design Validation",
        "Workflow Marketplace Design Validation",
        "Knowledge Exchange Design Validation",
        "Federation Architecture Design Validation",
    ):
        assert gate in gates
    for category in (
        "Creative Service Platform",
        "Plugin Ecosystem",
        "Workflow Marketplace",
        "Knowledge Exchange",
        "Federation Architecture",
    ):
        assert category in debt
