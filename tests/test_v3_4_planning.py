"""Planning contracts for the v3.4 design-only development cycle."""

from __future__ import annotations

import re
from pathlib import Path

import manga_director

ROOT = Path(__file__).resolve().parents[1]


def test_v3_4_planning_assets_preserve_the_v3_3_release_baseline() -> None:
    documents = (
        "docs/VISION_v3_4.md",
        "docs/ARCHITECTURE_V3_4.md",
        "docs/V3_4_ARCHITECTURE.md",
        "docs/ROADMAP_v3_4.md",
        "docs/GITHUB_V3_4_PLAN.md",
        "docs/KNOWLEDGE_PLATFORM.md",
        "docs/PRODUCTION_OPERATIONS.md",
        "docs/ORGANIZATION_INTELLIGENCE.md",
        "docs/RELEASE_INTELLIGENCE.md",
        "docs/V3_4_BENCHMARK_PLAN.md",
        "docs/V3_4_QUALITY_GATES.md",
        "docs/V3_4_DEVELOPMENT_PLANNING_REPORT.md",
    )

    assert manga_director.__version__ == "6.0.0"
    assert all((ROOT / document).is_file() for document in documents)
    architecture = (ROOT / "docs/ARCHITECTURE_V3_4.md").read_text(encoding="utf-8")
    vision = (ROOT / "docs/VISION_v3_4.md").read_text(encoding="utf-8")

    assert "does not change Core Architecture" in architecture
    assert "exactly one Page" in architecture
    assert "StateMachine" in vision


def test_v3_4_planning_examples_and_benchmarks_are_non_executing() -> None:
    assets = (
        "examples/knowledge_platform/README.md",
        "examples/production_operations/README.md",
        "examples/organization_intelligence/README.md",
        "examples/release_intelligence/README.md",
        "examples/release_dashboard/README.md",
        "benchmarks/v3_4/README.md",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
    assert all("design-only" in (ROOT / asset).read_text(encoding="utf-8") for asset in assets)


def test_v3_4_planning_documentation_links_are_resolvable() -> None:
    documents = [
        ROOT / "README.md",
        *sorted((ROOT / "docs").glob("*V3_4*.md")),
        ROOT / "docs/KNOWLEDGE_PLATFORM.md",
        ROOT / "docs/PRODUCTION_OPERATIONS.md",
        ROOT / "docs/ORGANIZATION_INTELLIGENCE.md",
        ROOT / "docs/RELEASE_INTELLIGENCE.md",
        *sorted((ROOT / "examples").glob("*/README.md")),
        ROOT / "benchmarks/v3_4/README.md",
    ]
    for document in documents:
        contents = document.read_text(encoding="utf-8")
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", contents):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            assert (document.parent / link).exists(), f"{document}: broken link to {link}"
