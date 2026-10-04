from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from manga_director.adapters.factory import ImageGeneratorFactory
from manga_director.adapters.mock_image_generator import MockImageGenerator
from manga_director.agents.registry import primary_agents, support_agents
from manga_director.domain.exceptions import PluginDependencyError, PluginRegistrationError
from manga_director.domain.state_machine import StateMachine
from manga_director.events import MemoryEventBus
from manga_director.plugins import (
    PluginDiscovery,
    PluginLoader,
    PluginManager,
    PluginRegistry,
    PluginType,
    apply_agent_plugins,
    apply_image_generator_plugins,
)
from manga_director.workflow import WorkflowContext, WorkflowEngine


def _write_plugin(
    root: Path,
    name: str,
    *,
    dependencies: list[str] | None = None,
    enabled: bool = True,
    preamble: str = "",
    body: str = "",
) -> str:
    directory = root / name
    directory.mkdir(parents=True)
    module_name = f"plugin_{name.replace('-', '_').replace('.', '_')}"
    manifest = "\n".join(
        [
            f"name: {name}",
            "version: 1.0.0",
            f"entry_point: {module_name}:SamplePlugin",
            f"dependencies: {dependencies or []}",
            f"enabled: {'true' if enabled else 'false'}",
            "description: test plugin",
            "",
        ]
    )
    (directory / "plugin.yaml").write_text(manifest, encoding="utf-8")
    registration = body or "        registry.register(\n"
    if not body:
        registration += (
            f"            PluginType.PROMPT, '{name}-fixture', object(), plugin_name=self.name\n"
            "        )"
        )
    (directory / f"{module_name}.py").write_text(
        "from manga_director.plugins import PluginType\n"
        "events = []\n"
        f"{preamble}"
        "class SamplePlugin:\n"
        f"    name = {name!r}\n"
        "    version = '1.0.0'\n"
        "    description = 'test plugin'\n"
        "    def initialize(self):\n"
        "        events.append('initialize')\n"
        "    def register(self, registry):\n"
        "        events.append('register')\n"
        f"{registration}\n"
        "    def shutdown(self):\n"
        "        events.append('shutdown')\n",
        encoding="utf-8",
    )
    return module_name


def test_registry_register_find_list_and_unregister() -> None:
    registry = PluginRegistry()
    contribution = registry.register(PluginType.PROMPT, "template", object(), plugin_name="fixture")

    assert registry.find("prompt", "template") == contribution
    assert registry.list(PluginType.PROMPT) == [contribution]
    assert registry.unregister("prompt", "template") == contribution
    assert registry.find(PluginType.PROMPT, "template") is None
    with pytest.raises(PluginRegistrationError):
        registry.unregister(PluginType.PROMPT, "template")


def test_discovery_reads_manifests_and_updates_enabled_state(tmp_path: Path) -> None:
    _write_plugin(tmp_path, "alpha", enabled=False)
    discovery = PluginDiscovery(tmp_path)

    assert discovery.discover()[0].manifest.enabled is False
    assert discovery.set_enabled("alpha", True).enabled is True
    assert discovery.discover()[0].manifest.enabled is True


def test_loader_imports_the_manifest_entry_point(tmp_path: Path) -> None:
    _write_plugin(tmp_path, "loaded")
    plugin = PluginLoader().load(PluginDiscovery(tmp_path).discover()[0])

    assert plugin.name == "loaded"
    assert plugin.description == "test plugin"


def test_manager_runs_lifecycle_and_unregisters_on_shutdown(tmp_path: Path) -> None:
    module_name = _write_plugin(tmp_path, "lifecycle")
    manager = PluginManager(tmp_path)

    assert [plugin.name for plugin in manager.load_enabled()] == ["lifecycle"]
    assert manager.registry.find(PluginType.PROMPT, "lifecycle-fixture") is not None
    manager.shutdown()

    module = importlib.import_module(module_name)
    assert module.events == ["initialize", "register", "shutdown"]
    assert manager.registry.list() == []


def test_manager_resolves_dependencies_before_dependents(tmp_path: Path) -> None:
    first_module = _write_plugin(tmp_path, "base")
    second_module = _write_plugin(tmp_path, "dependent", dependencies=["base"])
    manager = PluginManager(tmp_path)

    assert [plugin.name for plugin in manager.load_enabled()] == ["base", "dependent"]
    assert importlib.import_module(first_module).events[:2] == ["initialize", "register"]
    assert importlib.import_module(second_module).events[:2] == ["initialize", "register"]


def test_manager_rejects_missing_disabled_and_circular_dependencies(tmp_path: Path) -> None:
    _write_plugin(tmp_path, "missing", dependencies=["unknown"])
    with pytest.raises(PluginDependencyError, match="not found"):
        PluginManager(tmp_path).load_enabled()

    disabled_root = tmp_path / "disabled"
    _write_plugin(disabled_root, "base", enabled=False)
    _write_plugin(disabled_root, "dependent", dependencies=["base"])
    with pytest.raises(PluginDependencyError, match="disabled"):
        PluginManager(disabled_root).load_enabled()

    cycle_root = tmp_path / "cycle"
    _write_plugin(cycle_root, "left", dependencies=["right"])
    _write_plugin(cycle_root, "right", dependencies=["left"])
    with pytest.raises(PluginDependencyError, match="Circular"):
        PluginManager(cycle_root).load_enabled()


def test_image_and_agent_plugins_extend_outer_composition(tmp_path: Path) -> None:
    image_body = (
        "        registry.register(PluginType.IMAGE_GENERATOR, 'plugin-mock', "
        "lambda: __import__('manga_director.adapters.mock_image_generator', "
        "fromlist=['MockImageGenerator']).MockImageGenerator(), plugin_name=self.name)"
    )
    agent_body = (
        "        registry.register(PluginType.AGENT, 'plugin-support', FixtureAgent, "
        "plugin_name=self.name, metadata={'role': 'support', 'command': 'plugin-support'})"
    )
    _write_plugin(tmp_path, "image", body=image_body)
    _write_plugin(
        tmp_path,
        "agent",
        preamble=(
            "class FixtureAgent:\n"
            "    def execute(self, context):\n"
            "        from manga_director.workflow import AgentResult\n"
            "        return AgentResult(\n"
            "            success=True, state=context.state, payload={}, events=[], messages=[]\n"
            "        )\n\n"
        ),
        body=agent_body,
    )
    manager = PluginManager(tmp_path)
    manager.load_enabled()

    apply_image_generator_plugins(manager.registry)
    assert isinstance(ImageGeneratorFactory.create("plugin-mock"), MockImageGenerator)
    primary, support = apply_agent_plugins(
        manager.registry,
        primary_agents(MockImageGenerator()),
        support_agents(),
    )
    assert primary
    assert "plugin-support" in support
    result = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=MemoryEventBus(),
        agents=primary,
        support_agents=support,
    ).execute_support(WorkflowContext(), "plugin-support")
    assert result.completed_step == "plugin-support"
