import pytest

from manga_director.adapters import (
    AdapterLifecycleState,
    ImageBackendRuntime,
    LLMProviderRuntime,
)


def test_provider_lifecycle_transitions_without_calling_provider_generation() -> None:
    runtime = LLMProviderRuntime()

    assert {item.state for item in runtime.initialize()} == {AdapterLifecycleState.READY}
    assert {item.state for item in runtime.health_snapshot()} == {AdapterLifecycleState.HEALTHY}
    assert {item.state for item in runtime.shutdown()} == {AdapterLifecycleState.SHUTDOWN}


def test_backend_lifecycle_and_declared_metadata_validation() -> None:
    runtime = ImageBackendRuntime()

    assert runtime.lifecycle().summary()["ready"] == 0
    runtime.initialize()
    assert runtime.validate_preset("test", "test") == {"model": "mock-image"}
    assert runtime.validate_workflow("comfyui", {"format": "workflow-json"}) is True
    with pytest.raises(ValueError, match="Unknown preset"):
        runtime.validate_preset("mock", "missing")
    with pytest.raises(ValueError, match="Workflow format"):
        runtime.validate_workflow("comfyui", {"format": "other"})
