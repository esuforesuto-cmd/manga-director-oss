"""Official policy contracts for the v6.x LTS charter."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_lts_charter_documents_are_available_and_linked() -> None:
    documents = (
        "LTS_POLICY.md",
        "SUPPORTED_VERSIONS.md",
        "SECURITY_POLICY.md",
        "COMPATIBILITY_POLICY.md",
        "BACKPORT_POLICY.md",
        "END_OF_LIFE_POLICY.md",
    )

    assert all((ROOT / document).is_file() for document in documents)
    for document_name in documents:
        document = ROOT / document_name
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", document.read_text(encoding="utf-8")):
            if not link.startswith(("http://", "https://", "mailto:")):
                assert (document.parent / link).exists(), f"{document}: broken link to {link}"


def test_lts_charter_preserves_support_lifecycle_and_api_compatibility() -> None:
    lts = (ROOT / "LTS_POLICY.md").read_text(encoding="utf-8")
    compatibility = (ROOT / "COMPATIBILITY_POLICY.md").read_text(encoding="utf-8")
    backport = (ROOT / "BACKPORT_POLICY.md").read_text(encoding="utf-8")

    assert "`6.0.x`" in lts
    assert "Platform API v1.0" in compatibility
    assert "New features" in backport
