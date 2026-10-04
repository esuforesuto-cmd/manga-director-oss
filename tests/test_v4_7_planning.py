"""Contracts for the v4.7 Creative Decision Platform design cycle."""

from __future__ import annotations

import re
from pathlib import Path

import manga_director

ROOT = Path(__file__).resolve().parents[1]


def test_v4_7_planning_assets_keep_the_v4_6_release_baseline() -> None:
    documents = (
        "docs/VISION_V4_7.md",
        "docs/ARCHITECTURE_V4_7.md",
        "docs/DECISION_ENGINE.md",
        "docs/REVIEW_INTELLIGENCE.md",
        "docs/RECOMMENDATION_FRAMEWORK.md",
        "docs/APPROVAL_PLATFORM.md",
        "docs/EXECUTIVE_DASHBOARD.md",
        "docs/ROADMAP_V4_7.md",
        "docs/MIGRATION_V4_7.md",
        "docs/V4_7_DEVELOPMENT_PLANNING_REPORT.md",
    )

    assert manga_director.__version__ == "6.0.0"
    assert all((ROOT / document).is_file() for document in documents)

    vision = (ROOT / "docs/VISION_V4_7.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs/ARCHITECTURE_V4_7.md").read_text(encoding="utf-8")
    approval = (ROOT / "docs/APPROVAL_PLATFORM.md").read_text(encoding="utf-8")

    assert "does not authorize autonomous decisions or execution" in vision
    assert "StateMachine" in architecture
    assert "cannot persist evidence" in architecture
    assert "never replaces the domain approval transition" in approval


def test_v4_7_planning_links_quality_gates_and_debt_are_resolvable() -> None:
    documents = (
        ROOT / "docs/VISION_V4_7.md",
        ROOT / "docs/ARCHITECTURE_V4_7.md",
        ROOT / "docs/DECISION_ENGINE.md",
        ROOT / "docs/REVIEW_INTELLIGENCE.md",
        ROOT / "docs/RECOMMENDATION_FRAMEWORK.md",
        ROOT / "docs/APPROVAL_PLATFORM.md",
        ROOT / "docs/EXECUTIVE_DASHBOARD.md",
        ROOT / "docs/ROADMAP_V4_7.md",
        ROOT / "docs/MIGRATION_V4_7.md",
        ROOT / "docs/V4_7_DEVELOPMENT_PLANNING_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    for document in documents:
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", document.read_text(encoding="utf-8")):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            assert (document.parent / link).exists(), f"{document}: broken link to {link}"

    for gate in (
        "Decision Engine Design Validation",
        "Review Intelligence Design Validation",
        "Recommendation Framework Design Validation",
        "Approval Platform Design Validation",
        "Executive Dashboard Design Validation",
    ):
        assert gate in gates
    for category in (
        "Decision Engine",
        "Review Intelligence",
        "Recommendation Framework",
        "Approval Platform",
        "Executive Dashboard",
    ):
        assert category in debt
