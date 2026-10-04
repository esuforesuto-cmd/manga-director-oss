"""Contracts for the v4.3 Creative Production Platform design cycle."""

from __future__ import annotations

import re
from pathlib import Path

import manga_director

ROOT = Path(__file__).resolve().parents[1]


def test_v4_3_planning_assets_keep_the_v4_2_release_baseline() -> None:
    documents = (
        "docs/VISION_V4_3.md",
        "docs/CREATIVE_PRODUCTION_PLATFORM.md",
        "docs/PRODUCTION_PIPELINE.md",
        "docs/ASSET_MANAGEMENT.md",
        "docs/PUBLISHING_PLATFORM.md",
        "docs/PROJECT_OPERATIONS.md",
        "docs/CREATIVE_PRODUCTION_PLATFORM_TEST_PLAN.md",
        "docs/V4_3_DEVELOPMENT_PLANNING_REPORT.md",
    )

    assert manga_director.__version__ == "6.0.0"
    assert all((ROOT / document).is_file() for document in documents)

    vision = (ROOT / "docs/VISION_V4_3.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs/CREATIVE_PRODUCTION_PLATFORM.md").read_text(
        encoding="utf-8"
    )
    publishing = (ROOT / "docs/PUBLISHING_PLATFORM.md").read_text(encoding="utf-8")

    assert "does not authorize automatic publishing" in vision
    assert "StateMachine" in architecture
    assert "no authority to write" in architecture
    assert "does not export, publish, distribute" in publishing


def test_v4_3_examples_are_non_executable_and_keep_workflow_boundaries() -> None:
    examples = (
        "examples/production_pipeline/v4_3_design.md",
        "examples/asset_management/v4_3_design.md",
        "examples/publishing/v4_3_design.md",
        "examples/project_operations/v4_3_design.md",
    )
    contents = [(ROOT / example).read_text(encoding="utf-8") for example in examples]

    assert all((ROOT / example).is_file() for example in examples)
    assert all("non-executable" in content for content in contents)
    assert "at most one existing Page" in contents[0]
    assert "does not write an asset" in contents[1]
    assert "never\nexports" in contents[2]
    assert "does not create team\nmembers" in contents[3]


def test_v4_3_planning_links_quality_gates_and_debt_are_resolvable() -> None:
    documents = (
        ROOT / "docs/VISION_V4_3.md",
        ROOT / "docs/CREATIVE_PRODUCTION_PLATFORM.md",
        ROOT / "docs/PRODUCTION_PIPELINE.md",
        ROOT / "docs/ASSET_MANAGEMENT.md",
        ROOT / "docs/PUBLISHING_PLATFORM.md",
        ROOT / "docs/PROJECT_OPERATIONS.md",
        ROOT / "docs/CREATIVE_PRODUCTION_PLATFORM_TEST_PLAN.md",
        ROOT / "docs/V4_3_DEVELOPMENT_PLANNING_REPORT.md",
        ROOT / "examples/production_pipeline/v4_3_design.md",
        ROOT / "examples/asset_management/v4_3_design.md",
        ROOT / "examples/publishing/v4_3_design.md",
        ROOT / "examples/project_operations/v4_3_design.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    for document in documents:
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", document.read_text(encoding="utf-8")):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            assert (document.parent / link).exists(), f"{document}: broken link to {link}"

    for gate in (
        "Production Architecture Validation",
        "Asset Design Validation",
        "Publishing Design Validation",
        "Operations Design Validation",
    ):
        assert gate in gates
    for category in (
        "Production Platform",
        "Asset Management",
        "Publishing Platform",
        "Project Operations",
    ):
        assert category in debt
