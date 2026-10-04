"""Planning contracts for the v3.2 design-only development cycle."""

from __future__ import annotations

import re
from pathlib import Path

import manga_director

ROOT = Path(__file__).resolve().parents[1]


def test_v3_2_planning_assets_preserve_the_v3_1_release_baseline() -> None:
    documents = (
        "docs/VISION_v3_2.md",
        "docs/ARCHITECTURE_V3_2.md",
        "docs/V3_2_ARCHITECTURE.md",
        "docs/ROADMAP_v3_2.md",
        "docs/GITHUB_V3_2_PLAN.md",
        "docs/CREATIVE_STUDIO.md",
        "docs/ASSET_INTELLIGENCE.md",
        "docs/PRODUCTION_ANALYTICS.md",
        "docs/V3_2_BENCHMARK_PLAN.md",
        "docs/V3_2_QUALITY_GATES.md",
        "docs/UPGRADE_GUIDE_v3_2.md",
        "docs/V3_2_DEVELOPMENT_PLANNING_REPORT.md",
    )

    assert manga_director.__version__ == "6.0.0"
    assert all((ROOT / document).is_file() for document in documents)
    assert "does not change Core" in (ROOT / "docs/ARCHITECTURE_V3_2.md").read_text(
        encoding="utf-8"
    )
    vision = (ROOT / "docs/VISION_v3_2.md").read_text(encoding="utf-8")
    assert "exactly one Page" in vision
    assert "StateMachine" in vision


def test_v3_2_planning_examples_and_benchmarks_are_non_executing() -> None:
    examples = (
        "examples/creative_studio/README.md",
        "examples/asset_intelligence/README.md",
        "examples/workflow_profiles/README.md",
        "examples/production_analytics/README.md",
        "examples/project_dashboard/README.md",
        "benchmarks/v3_2/README.md",
    )

    assert all((ROOT / example).is_file() for example in examples)
    assert all(
        "design-only" in (ROOT / example).read_text(encoding="utf-8") for example in examples
    )


def test_v3_2_planning_documentation_links_are_resolvable() -> None:
    documents = [
        ROOT / "README.md",
        *sorted((ROOT / "docs").glob("*v3_2.md")),
        *sorted((ROOT / "docs").glob("V3_2*.md")),
    ]
    for document in documents:
        contents = document.read_text(encoding="utf-8")
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", contents):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            assert (document.parent / link).exists(), f"{document}: broken link to {link}"
