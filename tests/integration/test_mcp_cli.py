import hashlib
from pathlib import Path

from typer.testing import CliRunner

from manga_director.cli.app import app


def _tree_manifest(root: Path) -> tuple[tuple[str, str], ...]:
    entries: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        if path.is_dir():
            entries.append((relative, "directory"))
        elif path.is_file():
            entries.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
    return tuple(entries)


def test_cli_lists_mcp_tools_resources_and_prompts(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    common = ["--config", str(config)]

    tools = runner.invoke(app, ["mcp", "tools", *common])
    resources = runner.invoke(app, ["mcp", "resources", *common])
    prompts = runner.invoke(app, ["mcp", "prompts", *common])

    assert tools.exit_code == 0
    assert '"name": "create_project"' in tools.stdout
    assert resources.exit_code == 0
    assert '"uri": "manga://projects"' in resources.stdout
    assert prompts.exit_code == 0
    assert '"name": "design_manga_page"' in prompts.stdout


def test_cli_mcp_server_build_does_not_create_localfile_durability_sidecars(tmp_path: Path) -> None:
    runner = CliRunner()
    config = tmp_path / "config.yaml"
    common = ["--config", str(config)]
    created = runner.invoke(app, ["project", "create", "--id", "demo", "--title", "Demo", *common])
    before = _tree_manifest(tmp_path)

    tools = runner.invoke(app, ["mcp", "tools", *common])

    assert created.exit_code == 0
    assert tools.exit_code == 0
    assert '"name": "get_project_status"' in tools.stdout
    assert _tree_manifest(tmp_path) == before
