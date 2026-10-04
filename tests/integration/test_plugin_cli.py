from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from manga_director.cli.app import app


def _plugin_source(root: Path) -> Path:
    source = root / "source"
    source.mkdir()
    (source / "plugin.yaml").write_text(
        "\n".join(
            [
                "name: local-plugin",
                "version: 1.0.0",
                "entry_point: local_plugin:LocalPlugin",
                "dependencies: []",
                "enabled: true",
                "description: CLI fixture",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (source / "local_plugin.py").write_text(
        "class LocalPlugin:\n"
        "    name = 'local-plugin'\n"
        "    version = '1.0.0'\n"
        "    description = 'CLI fixture'\n"
        "    def initialize(self): pass\n"
        "    def register(self, registry): pass\n"
        "    def shutdown(self): pass\n",
        encoding="utf-8",
    )
    return source


def test_plugin_cli_installs_lists_toggles_and_removes_local_plugin(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    source = _plugin_source(tmp_path)

    installed = runner.invoke(
        app,
        ["plugin", "install", "--source", str(source), "--config", str(config)],
    )
    assert installed.exit_code == 0, installed.output
    listed = runner.invoke(app, ["plugin", "list", "--config", str(config)])
    assert listed.exit_code == 0, listed.output
    assert "local-plugin" in listed.output
    disabled = runner.invoke(app, ["plugin", "disable", "local-plugin", "--config", str(config)])
    assert disabled.exit_code == 0, disabled.output
    removed = runner.invoke(app, ["plugin", "remove", "local-plugin", "--config", str(config)])
    assert removed.exit_code == 0, removed.output
