"""Deterministic local security evidence for the frozen v6.0 source scope."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V6_SOURCE_FILES = (
    ROOT / "src" / "manga_director" / "production" / "v6_0_foundation.py",
    ROOT / "src" / "manga_director" / "production" / "v6_0_intelligence.py",
    ROOT / "src" / "manga_director" / "production" / "v6_0_platform_core.py",
)
SECRET_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "AWS-key": re.compile(r"AKIA[0-9A-Z]{16}"),
}


def test_lts_security_evidence_scope_matches_the_v6_audit_record() -> None:
    audit = " ".join((ROOT / "docs" / "SECURITY_AUDIT_V6_0.md").read_text(encoding="utf-8").split())
    maintenance = (ROOT / "docs" / "SECURITY_MAINTENANCE.md").read_text(encoding="utf-8")

    assert all(path.is_file() for path in V6_SOURCE_FILES)
    assert "Platform Foundation, Intelligence, and Platform Kernel source paths" in audit
    assert "private-key/AWS-key pattern scans" in audit
    assert "common secret patterns" in maintenance


def test_lts_security_evidence_has_no_documented_secret_pattern_matches() -> None:
    for pattern_name, pattern in SECRET_PATTERNS.items():
        matched_files = tuple(
            path.relative_to(ROOT).as_posix()
            for path in V6_SOURCE_FILES
            if pattern.search(path.read_text(encoding="utf-8"))
        )

        assert not matched_files, f"{pattern_name} pattern detected in: {', '.join(matched_files)}"
