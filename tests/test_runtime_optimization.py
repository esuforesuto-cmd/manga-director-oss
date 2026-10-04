"""Contracts for cached runtime boundaries; all optimizations remain additive."""

from __future__ import annotations

import json
from pathlib import Path

from pytest import MonkeyPatch

from benchmarks import (
    configuration_load,
    event_dispatch,
    extension_loading,
    plugin_loading,
)
from benchmarks import diagnostics as diagnostics_benchmark
from manga_director.cli.config import (
    clear_config_cache,
    configuration_diagnostics,
    load_config,
)
from manga_director.domain.events import EventType, WorkflowEvent
from manga_director.events import MemoryEventBus
from manga_director.observability import MetricsRegistry, RuntimeDiagnostics
from manga_director.plugins import PluginDiscovery, PluginManager
from manga_director.sdk import ExtensionValidator


def _write_plugin(root: Path, name: str, *, dependencies: list[str] | None = None) -> None:
    directory = root / name
    directory.mkdir(parents=True)
    module_name = f"runtime_plugin_{name}"
    (directory / "plugin.yaml").write_text(
        "\n".join(
            [
                f"name: {name}",
                "version: 1.0.0",
                f"entry_point: {module_name}:RuntimePlugin",
                f"dependencies: {dependencies or []}",
                "enabled: true",
                "description: runtime fixture",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (directory / f"{module_name}.py").write_text(
        "class RuntimePlugin:\n"
        f"    name = {name!r}\n"
        "    version = '1.0.0'\n"
        "    description = 'runtime fixture'\n"
        "    def initialize(self): pass\n"
        "    def register(self, registry): pass\n"
        "    def shutdown(self): pass\n",
        encoding="utf-8",
    )


def test_plugin_discovery_cache_and_lazy_load_keep_plugin_contract(tmp_path: Path) -> None:
    _write_plugin(tmp_path, "base")
    _write_plugin(tmp_path, "feature", dependencies=["base"])
    discovery = PluginDiscovery(tmp_path)

    first = discovery.discover()
    second = discovery.discover()

    assert first[0] is second[0]
    manager = PluginManager(tmp_path)
    assert [plugin.name for plugin in manager.load("feature")] == ["base", "feature"]
    assert manager.diagnostics()["dependency_cache_entries"] == 1


def test_extension_validator_caches_manifest_and_compatibility(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(
        """id: runtime-extension
name: Runtime Extension
version: 1.0.0
author: tests
license: MIT
description: cached fixture
entry_point: manga_director.sdk.extension:Extension
""",
        encoding="utf-8",
    )
    validator = ExtensionValidator()

    assert validator.load(manifest_path) is validator.load(manifest_path)
    assert validator.diagnostics()["manifest_cache_entries"] == 1
    assert validator.diagnostics()["compatibility_cache_entries"] == 1


def test_memory_event_bus_caches_subscriptions_and_prevents_duplicate_event_ids() -> None:
    bus = MemoryEventBus()
    received: list[WorkflowEvent] = []
    bus.subscribe(EventType.PAGE_DESIGNED, received.append)
    bus.subscribe(EventType.PAGE_DESIGNED, received.append)
    event = WorkflowEvent(event_type=EventType.PAGE_DESIGNED)

    bus.publish([event, event])

    assert received == [event]
    assert bus.diagnostics()["subscriptions"] == 1
    assert bus.diagnostics()["duplicate_events"] == 1


def test_configuration_cache_reloads_after_file_or_environment_change(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("repository:\n  root: ${MANGA_DIRECTOR_RUNTIME_ROOT}\n", encoding="utf-8")
    monkeypatch.setenv("MANGA_DIRECTOR_RUNTIME_ROOT", "first")
    clear_config_cache(config_path)

    first = load_config(config_path)
    cached = load_config(config_path)
    monkeypatch.setenv("MANGA_DIRECTOR_RUNTIME_ROOT", "second")
    reloaded = load_config(config_path)

    assert first is cached
    assert first.repository.root == Path("first")
    assert reloaded.repository.root == Path("second")
    assert configuration_diagnostics(config_path)["requested_cached"] == 1


def test_runtime_diagnostics_composes_safe_runtime_snapshots() -> None:
    metrics = MetricsRegistry()
    metrics.observe("runtime.duration_seconds", 0.01)
    report = RuntimeDiagnostics(metrics).report(
        plugins={"active": []},
        extensions={"manifest_cache_entries": 1},
        configuration={"cache_entries": 1},
        repositories={"operations": 2},
        events={"published": 3},
    )

    assert report.system["python_version"]
    assert report.plugins["active"] == []
    assert report.extensions["manifest_cache_entries"] == 1
    assert report.configuration["cache_entries"] == 1
    assert report.events["published"] == 3


def test_runtime_performance_regression_smoke() -> None:
    """Detect a material runtime-boundary slowdown while allowing local variance."""

    elapsed = {
        "plugin_loading": plugin_loading.run(plugin_count=10),
        "extension_loading": extension_loading.run(iterations=100),
        "event_dispatch": event_dispatch.run(event_count=200, listener_count=4),
        "configuration_load": configuration_load.run(iterations=100),
        "diagnostics": diagnostics_benchmark.run(iterations=100),
    }
    baseline = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "benchmarks"
            / "baselines"
            / "v2_2_iteration_1_runtime.json"
        ).read_text(encoding="utf-8")
    )

    for name, value in elapsed.items():
        assert value <= max(
            baseline[name] * baseline["multiplier"], baseline["minimum_threshold_seconds"]
        ), (name, value)
