"""Planning contracts for the v3.5 design-only development cycle."""

from __future__ import annotations

import re
from pathlib import Path

import manga_director

ROOT = Path(__file__).resolve().parents[1]


def test_v3_5_planning_assets_preserve_the_v3_4_release_baseline() -> None:
    documents = (
        "docs/VISION_v3_5.md",
        "docs/ARCHITECTURE_V3_5.md",
        "docs/V3_5_ARCHITECTURE.md",
        "docs/MIGRATION_STRATEGY_V3_5.md",
        "docs/ROADMAP_v3_5.md",
        "docs/GITHUB_V3_5_PLAN.md",
        "docs/UNIFIED_KNOWLEDGE_GRAPH.md",
        "docs/CREATIVE_INTELLIGENCE.md",
        "docs/PRODUCTION_INTELLIGENCE_V3_5.md",
        "docs/PLATFORM_ANALYTICS.md",
        "docs/V3_5_BENCHMARK_PLAN.md",
        "docs/V3_5_QUALITY_GATES.md",
        "docs/V3_5_DEVELOPMENT_PLANNING_REPORT.md",
    )

    assert manga_director.__version__ == "6.0.0"
    assert all((ROOT / document).is_file() for document in documents)
    architecture = (ROOT / "docs/ARCHITECTURE_V3_5.md").read_text(encoding="utf-8")
    vision = (ROOT / "docs/VISION_v3_5.md").read_text(encoding="utf-8")

    assert "does not change Core Architecture" in architecture
    assert "exactly one Page" in architecture
    assert "StateMachine" in vision


def test_v3_5_planning_examples_and_benchmarks_are_non_executing() -> None:
    assets = (
        "examples/v3_5/knowledge_graph/README.md",
        "examples/v3_5/creative_intelligence/README.md",
        "examples/v3_5/production_intelligence/README.md",
        "examples/v3_5/platform_analytics/README.md",
        "examples/v3_5/executive_dashboard/README.md",
        "benchmarks/v3_5/README.md",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
    assert all("design-only" in (ROOT / asset).read_text(encoding="utf-8") for asset in assets)


def test_v3_5_planning_documentation_links_are_resolvable() -> None:
    documents = [
        ROOT / "README.md",
        *sorted((ROOT / "docs").glob("*V3_5*.md")),
        ROOT / "docs/UNIFIED_KNOWLEDGE_GRAPH.md",
        ROOT / "docs/CREATIVE_INTELLIGENCE.md",
        ROOT / "docs/PLATFORM_ANALYTICS.md",
        *sorted((ROOT / "examples/v3_5").glob("*/README.md")),
        ROOT / "benchmarks/v3_5/README.md",
    ]
    for document in documents:
        contents = document.read_text(encoding="utf-8")
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", contents):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            assert (document.parent / link).exists(), f"{document}: broken link to {link}"
