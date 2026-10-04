"""Planning contracts for the v3.3 design-only development cycle."""

from __future__ import annotations

import re
from pathlib import Path

import manga_director

ROOT = Path(__file__).resolve().parents[1]


def test_v3_3_planning_assets_preserve_the_v3_2_release_baseline() -> None:
    documents = (
        "docs/VISION_v3_3.md",
        "docs/ARCHITECTURE_V3_3.md",
        "docs/V3_3_ARCHITECTURE.md",
        "docs/ROADMAP_v3_3.md",
        "docs/GITHUB_V3_3_PLAN.md",
        "docs/PRODUCTION_PIPELINE.md",
        "docs/QUALITY_INTELLIGENCE.md",
        "docs/ASSET_LIFECYCLE.md",
        "docs/V3_3_BENCHMARK_PLAN.md",
        "docs/V3_3_QUALITY_GATES.md",
        "docs/UPGRADE_GUIDE_v3_3.md",
        "docs/V3_3_DEVELOPMENT_PLANNING_REPORT.md",
    )

    assert manga_director.__version__ == "6.0.0"
    assert all((ROOT / document).is_file() for document in documents)
    architecture = (ROOT / "docs/ARCHITECTURE_V3_3.md").read_text(encoding="utf-8")
    vision = (ROOT / "docs/VISION_v3_3.md").read_text(encoding="utf-8")

    assert "does not change Core" in architecture
    assert "exactly one Page" in vision
    assert "StateMachine" in vision


def test_v3_3_planning_examples_and_benchmarks_are_non_executing() -> None:
    examples = (
        "examples/production_pipeline/README.md",
        "examples/quality_dashboard/README.md",
        "examples/asset_lifecycle/README.md",
        "examples/project_intelligence/README.md",
        "examples/delivery_forecast/README.md",
        "benchmarks/v3_3/README.md",
    )

    assert all((ROOT / example).is_file() for example in examples)
    assert all(
        "design-only" in (ROOT / example).read_text(encoding="utf-8") for example in examples
    )


def test_v3_3_planning_documentation_links_are_resolvable() -> None:
    documents = [
        ROOT / "README.md",
        *sorted((ROOT / "docs").glob("*v3_3.md")),
        *sorted((ROOT / "docs").glob("V3_3*.md")),
    ]
    for document in documents:
        contents = document.read_text(encoding="utf-8")
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", contents):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            assert (document.parent / link).exists(), f"{document}: broken link to {link}"
