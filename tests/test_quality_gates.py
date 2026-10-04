"""Fast repository-level quality gates kept independent from delivery adapters."""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

import manga_director
from manga_director import Director, Page, Project, Repository, WorkflowContext, WorkflowEngine

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "manga_director"
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^]]*\]\(([^)]+)\)")


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }


def test_domain_has_no_outward_manga_director_dependencies() -> None:
    """The domain layer stays independent from application and infrastructure layers."""

    forbidden = (
        "manga_director.adapters",
        "manga_director.agents",
        "manga_director.api",
        "manga_director.cli",
        "manga_director.events",
        "manga_director.mcp",
        "manga_director.repositories",
        "manga_director.workflow",
    )
    imported = {
        module for path in (SOURCE / "domain").rglob("*.py") for module in _imported_modules(path)
    }
    assert not any(module.startswith(forbidden) for module in imported)


def test_page_engine_does_not_depend_on_delivery_or_repository_adapters() -> None:
    """The page engine retains its narrow orchestration responsibility."""

    imported = _imported_modules(SOURCE / "workflow" / "engine.py")
    forbidden = (
        "manga_director.adapters",
        "manga_director.agents",
        "manga_director.api",
        "manga_director.cli",
        "manga_director.mcp",
        "manga_director.repositories",
    )
    assert not any(module.startswith(forbidden) for module in imported)


def test_public_api_imports_remain_available() -> None:
    """Catch accidental package-boundary regressions before distribution."""

    assert manga_director.__version__
    assert all((Director, WorkflowEngine, WorkflowContext, Project, Page, Repository))


def test_declared_dependencies_are_unique() -> None:
    """Prevent duplicate direct and optional distribution dependencies."""

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    dependency_groups = [project["dependencies"], *project["optional-dependencies"].values()]
    names = [
        requirement.split("[", 1)[0].split("=", 1)[0].split(">", 1)[0].lower()
        for group in dependency_groups
        for requirement in group
    ]
    assert len(names) == len(set(names))


def test_documented_local_markdown_links_resolve() -> None:
    """Verify local README and docs links without requiring a documentation server."""

    markdown_files = [ROOT / "README.md", *(ROOT / "docs").rglob("*.md")]
    missing: list[str] = []
    for document in markdown_files:
        for raw_target in MARKDOWN_LINK.findall(document.read_text(encoding="utf-8")):
            target = raw_target.split("#", 1)[0].strip().strip("<>")
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            if not (document.parent / target).resolve().exists():
                missing.append(f"{document.relative_to(ROOT)} -> {raw_target}")
    assert not missing, "Broken local Markdown links:\n" + "\n".join(missing)
