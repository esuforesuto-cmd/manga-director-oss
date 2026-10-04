"""Contracts for the v4.6 Creative Intelligence OS design cycle."""

from __future__ import annotations

import re
from pathlib import Path

import manga_director

ROOT = Path(__file__).resolve().parents[1]


def test_v4_6_planning_assets_keep_the_v4_5_release_baseline() -> None:
    documents = (
        "docs/VISION_V4_6.md",
        "docs/ARCHITECTURE_V4_6.md",
        "docs/UNIFIED_CREATIVE_CONTEXT.md",
        "docs/CREATIVE_REASONING.md",
        "docs/ADAPTIVE_WORKFLOW.md",
        "docs/INTELLIGENCE_HUB.md",
        "docs/ROADMAP_V4_6.md",
        "docs/MIGRATION_V4_6.md",
        "docs/V4_6_DEVELOPMENT_PLANNING_REPORT.md",
    )

    assert manga_director.__version__ == "6.0.0"
    assert all((ROOT / document).is_file() for document in documents)

    vision = (ROOT / "docs/VISION_V4_6.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs/ARCHITECTURE_V4_6.md").read_text(encoding="utf-8")
    workflow = (ROOT / "docs/ADAPTIVE_WORKFLOW.md").read_text(encoding="utf-8")

    assert "does not authorize autonomous AI decisions or execution" in vision
    assert "StateMachine" in architecture
    assert "has no authority to" in architecture
    assert "exactly one page per workflow execution" in workflow


def test_v4_6_planning_links_quality_gates_and_debt_are_resolvable() -> None:
    documents = (
        ROOT / "docs/VISION_V4_6.md",
        ROOT / "docs/ARCHITECTURE_V4_6.md",
        ROOT / "docs/UNIFIED_CREATIVE_CONTEXT.md",
        ROOT / "docs/CREATIVE_REASONING.md",
        ROOT / "docs/ADAPTIVE_WORKFLOW.md",
        ROOT / "docs/INTELLIGENCE_HUB.md",
        ROOT / "docs/ROADMAP_V4_6.md",
        ROOT / "docs/MIGRATION_V4_6.md",
        ROOT / "docs/V4_6_DEVELOPMENT_PLANNING_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    for document in documents:
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", document.read_text(encoding="utf-8")):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            assert (document.parent / link).exists(), f"{document}: broken link to {link}"

    for gate in (
        "Unified Creative Context Design Validation",
        "Cross-Agent Memory Design Validation",
        "Creative Reasoning Design Validation",
        "Adaptive Workflow Design Validation",
        "Intelligence Hub Design Validation",
    ):
        assert gate in gates
    for category in (
        "Unified Creative Context",
        "Cross-Agent Memory",
        "Creative Reasoning",
        "Adaptive Workflow",
        "Intelligence Hub",
    ):
        assert category in debt
