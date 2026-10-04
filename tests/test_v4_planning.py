"""Contracts for the v4 Creative Operating System planning baseline."""

from __future__ import annotations

import re
from pathlib import Path

import manga_director

ROOT = Path(__file__).resolve().parents[1]


def test_v4_planning_assets_preserve_the_v3_5_release_baseline() -> None:
    documents = (
        "docs/VISION_V4.md",
        "docs/ARCHITECTURE_V4.md",
        "docs/CREATIVE_WORKSPACE_V2.md",
        "docs/CREATIVE_MEMORY.md",
        "docs/CREATIVE_GRAPH.md",
        "docs/CREATIVE_QUALITY.md",
        "docs/V4_QUALITY_GATES.md",
        "docs/V4_DEVELOPMENT_PLANNING_REPORT.md",
    )

    assert manga_director.__version__ == "6.0.0"
    assert all((ROOT / document).is_file() for document in documents)
    architecture = (ROOT / "docs/ARCHITECTURE_V4.md").read_text(encoding="utf-8")
    vision = (ROOT / "docs/VISION_V4.md").read_text(encoding="utf-8")

    assert "does not\nchange Core Architecture" in architecture
    assert "exactly one Page" in architecture
    assert "StateMachine" in vision
    assert "autonomous AI execution" in vision


def test_v4_planning_examples_and_benchmarks_are_design_only() -> None:
    assets = (
        "examples/workspace_v2/README.md",
        "examples/creative_memory/README.md",
        "examples/creative_graph/README.md",
        "examples/creative_quality/README.md",
        "benchmarks/v4/README.md",
        "benchmarks/v4/workspace.md",
        "benchmarks/v4/memory.md",
        "benchmarks/v4/graph.md",
        "benchmarks/v4/quality.md",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
    assert all("design-only" in (ROOT / asset).read_text(encoding="utf-8") for asset in assets[:5])


def test_v4_planning_documentation_links_and_quality_gates_are_resolvable() -> None:
    documents = (
        ROOT / "README.md",
        ROOT / "docs/VISION_V4.md",
        ROOT / "docs/ARCHITECTURE_V4.md",
        ROOT / "docs/CREATIVE_WORKSPACE_V2.md",
        ROOT / "docs/CREATIVE_MEMORY.md",
        ROOT / "docs/CREATIVE_GRAPH.md",
        ROOT / "docs/CREATIVE_QUALITY.md",
        ROOT / "docs/V4_QUALITY_GATES.md",
        ROOT / "docs/V4_DEVELOPMENT_PLANNING_REPORT.md",
        ROOT / "benchmarks/v4/README.md",
        ROOT / "examples/workspace_v2/README.md",
        ROOT / "examples/creative_memory/README.md",
        ROOT / "examples/creative_graph/README.md",
        ROOT / "examples/creative_quality/README.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")

    for document in documents:
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", document.read_text(encoding="utf-8")):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            assert (document.parent / link).exists(), f"{document}: broken link to {link}"
    assert "Workspace Validation" in gates
    assert "Memory Validation" in gates
    assert "Graph Validation" in gates
    assert "Creative Quality Validation" in gates
