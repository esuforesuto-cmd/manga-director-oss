"""Contract tests for passive provider and image-backend runtime discovery."""

from manga_director.adapters import ImageBackendRuntime, LLMProviderRuntime


def test_provider_discovery_capabilities_aliases_and_priority_are_available() -> None:
    runtime = LLMProviderRuntime()

    providers = runtime.discover()

    assert providers[0].name == "mock"
    assert runtime.resolve("default") == "mock"
    assert runtime.resolve("mock-llm") == "mock"
    assert "mock" in runtime.capability_report()["text"]
    assert runtime.model_report()["mock"] == ["mock-llm"]


def test_provider_diagnostics_are_safe_json_and_markdown() -> None:
    report = LLMProviderRuntime().report()

    assert report.summary["registered"] >= 1
    assert report.summary["healthy"] == report.summary["registered"]
    assert '"kind": "provider"' in report.to_json()
    assert "# Provider Runtime Report" in report.to_markdown()
    assert LLMProviderRuntime().fallback_policy(("mock",)).enabled is False


def test_provider_fallback_simulation_is_declarative_and_keeps_discovery_stable() -> None:
    runtime = LLMProviderRuntime()
    before = runtime.evaluate_priority()

    policy = runtime.fallback_simulation()

    assert policy.providers == tuple(before)
    assert policy.enabled is False
    assert runtime.evaluate_priority() == before


def test_backend_discovery_exposes_capabilities_workflow_metadata_and_presets() -> None:
    runtime = ImageBackendRuntime()

    assert runtime.resolve("test") == "mock"
    assert "comfyui" in runtime.capability_report()["workflow"]
    assert runtime.model_report()["mock"] == ["mock-image"]
    assert runtime.preset_report()["mock"] == ["test"]
    assert runtime.report().kind == "image backend"
