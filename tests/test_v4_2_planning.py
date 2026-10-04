"""Contracts for the v4.2 Autonomous Creative System design cycle."""

from __future__ import annotations

import re
from pathlib import Path

import manga_director

ROOT = Path(__file__).resolve().parents[1]


def test_v4_2_planning_assets_preserve_the_v4_1_release_baseline() -> None:
    documents = (
        "docs/VISION_V4_2.md",
        "docs/AUTONOMOUS_SYSTEM.md",
        "docs/EXECUTION_ENGINE.md",
        "docs/SUPERVISOR_FRAMEWORK.md",
        "docs/SAFETY_FRAMEWORK.md",
        "docs/CREATIVE_PIPELINE.md",
        "docs/AUTONOMOUS_EXECUTION_TEST_PLAN.md",
        "docs/SUPERVISOR_TEST_PLAN.md",
        "docs/SAFETY_TEST_PLAN.md",
        "docs/PIPELINE_TEST_PLAN.md",
        "docs/AUTONOMOUS_CREATIVE_SYSTEM_ARCHITECTURE_REPORT.md",
        "docs/V4_2_DEVELOPMENT_PLANNING_REPORT.md",
    )

    assert manga_director.__version__ == "6.0.0"
    assert all((ROOT / document).is_file() for document in documents)

    vision = (ROOT / "docs/VISION_V4_2.md").read_text(encoding="utf-8")
    system = (ROOT / "docs/AUTONOMOUS_SYSTEM.md").read_text(encoding="utf-8")
    safety = (ROOT / "docs/SAFETY_FRAMEWORK.md").read_text(encoding="utf-8")

    assert "does not authorize autonomous execution" in vision
    assert "one Page scoped" in system
    assert "StateMachine" in system
    assert "No lower policy may override" in safety


def test_v4_2_examples_are_design_only_and_keep_workflow_boundaries() -> None:
    examples = (
        "examples/autonomous_execution/v4_2_design.md",
        "examples/supervisor/v4_2_design.md",
        "examples/creative_pipeline/v4_2_design.md",
    )

    assert all((ROOT / example).is_file() for example in examples)
    contents = [(ROOT / example).read_text(encoding="utf-8") for example in examples]
    assert all(
        "not executable" in content or "non-executable" in content or "never dispatches" in content
        for content in contents
    )
    assert "at most one legal Page action" in contents[2]


def test_v4_2_planning_links_quality_gates_and_debt_are_resolvable() -> None:
    documents = (
        ROOT / "docs/VISION_V4_2.md",
        ROOT / "docs/AUTONOMOUS_SYSTEM.md",
        ROOT / "docs/EXECUTION_ENGINE.md",
        ROOT / "docs/SUPERVISOR_FRAMEWORK.md",
        ROOT / "docs/SAFETY_FRAMEWORK.md",
        ROOT / "docs/CREATIVE_PIPELINE.md",
        ROOT / "docs/AUTONOMOUS_CREATIVE_SYSTEM_ARCHITECTURE_REPORT.md",
        ROOT / "docs/V4_2_DEVELOPMENT_PLANNING_REPORT.md",
        ROOT / "examples/autonomous_execution/v4_2_design.md",
        ROOT / "examples/supervisor/v4_2_design.md",
        ROOT / "examples/creative_pipeline/v4_2_design.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    for document in documents:
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", document.read_text(encoding="utf-8")):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            assert (document.parent / link).exists(), f"{document}: broken link to {link}"

    for gate in (
        "Autonomous Architecture Validation",
        "Supervisor Design Validation",
        "Safety Design Validation",
        "Pipeline Design Validation",
    ):
        assert gate in gates
    for category in (
        "Autonomous System",
        "Supervisor Framework",
        "Safety Framework",
        "Creative Pipeline",
    ):
        assert category in debt
