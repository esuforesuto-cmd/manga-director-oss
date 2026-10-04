"""Structured v6.0 LTS Platform Kernel baseline contracts."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import manga_director
from benchmarks.v6_0_platform_rc1 import run as run_platform_kernel_benchmark

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "benchmarks" / "baselines" / "v6_0_platform_kernel.json"


def test_v6_platform_kernel_baseline_manifest_matches_the_lts_contract() -> None:
    assert MANIFEST_PATH.is_file()

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    iterations = inspect.signature(run_platform_kernel_benchmark).parameters[
        "iterations"
    ].default

    assert manifest["scenario"] == "v6_0_platform_kernel"
    assert manifest["benchmark_module"] == "benchmarks.v6_0_platform_rc1"
    assert manifest["target_version"] == manga_director.__version__ == "6.0.0"
    assert manifest["iterations"] == iterations == 500
    assert manifest["execution_scope"] == "local-only"
    assert manifest["page_scope"] == "single-page"
    assert manifest["operation_mode"] == "read-only, non-executing"
    assert manifest["persistence"] == "none"
    assert manifest["providers"] == "none"
    assert manifest["timing_threshold"] is None
    assert manifest["cross_version_comparison"] is False
    assert "minimum_threshold_seconds" not in manifest
    assert "multiplier" not in manifest
