"""Documentation contracts for v6.0 Creative Production Platform planning."""

from __future__ import annotations

from pathlib import Path

import manga_director

ROOT = Path(__file__).resolve().parents[1]


def test_v6_0_planning_artifacts_and_v5_7_baseline_are_available() -> None:
    documents = (
        "docs/VISION_V6_0.md",
        "docs/ARCHITECTURE_V6_0.md",
        "docs/PLATFORM_BLUEPRINT.md",
        "docs/COLLABORATION_FRAMEWORK.md",
        "docs/KNOWLEDGE_PLATFORM.md",
        "docs/AUTOMATION_PLATFORM.md",
        "docs/ENTERPRISE_FOUNDATION.md",
        "docs/ROADMAP_V6.md",
        "docs/MIGRATION_V5_7_TO_V6_0.md",
    )

    assert manga_director.__version__ == "6.0.0"
    assert all((ROOT / document).is_file() for document in documents)


def test_v6_0_architecture_preserves_v5_boundaries_and_workflow_invariants() -> None:
    architecture = (ROOT / "docs/ARCHITECTURE_V6_0.md").read_text(encoding="utf-8")
    migration = (ROOT / "docs/MIGRATION_V5_7_TO_V6_0.md").read_text(encoding="utf-8")
    automation = (ROOT / "docs/AUTOMATION_PLATFORM.md").read_text(encoding="utf-8")

    assert "StateMachine" in architecture
    assert "v5.x" in migration
    assert "persisted storyboard" in automation
    assert "completed quality review" in automation
