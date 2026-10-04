"""Measure cached plugin discovery, dependency ordering, and initialization."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from manga_director.plugins import PluginManager


def run(plugin_count: int = 20) -> float:
    with TemporaryDirectory(ignore_cleanup_errors=True) as root:
        directory = Path(root)
        for index in range(plugin_count):
            _write_plugin(directory, index)
        manager = PluginManager(directory)
        started = perf_counter()
        manager.discover()
        manager.discover()
        manager.load_enabled()
        elapsed = perf_counter() - started
        manager.shutdown()
        return elapsed


def _write_plugin(root: Path, index: int) -> None:
    name = f"runtime-{index}"
    directory = root / name
    directory.mkdir()
    module_name = f"benchmark_plugin_{index}"
    dependencies = "[]" if index == 0 else f"[runtime-{index - 1}]"
    (directory / "plugin.yaml").write_text(
        f"name: {name}\nversion: 1.0.0\nentry_point: {module_name}:Plugin\n"
        f"dependencies: {dependencies}\nenabled: true\ndescription: benchmark\n",
        encoding="utf-8",
    )
    (directory / f"{module_name}.py").write_text(
        "class Plugin:\n"
        f"    name = {name!r}\n"
        "    version = '1.0.0'\n"
        "    description = 'benchmark'\n"
        "    def initialize(self): pass\n"
        "    def register(self, registry): pass\n"
        "    def shutdown(self): pass\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    print(f"plugin_loading: {run():.6f}s")
