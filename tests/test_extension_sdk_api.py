"""Public import contracts for the stable Extension SDK."""

from __future__ import annotations

import manga_director.sdk as sdk


def test_extension_sdk_exports_the_stable_runtime_contract() -> None:
    expected = {
        "AgentExtension",
        "CLIExtension",
        "Extension",
        "ExtensionContext",
        "ExtensionLoader",
        "ExtensionManifest",
        "ExtensionValidator",
        "FastAPIExtension",
        "ImageGeneratorExtension",
        "LLMExtension",
        "MCPToolExtension",
        "NotificationExtension",
        "PromptExtension",
        "RepositoryExtension",
        "WorkflowExtension",
    }

    assert expected <= set(sdk.__all__)
    assert all(hasattr(sdk, name) for name in expected)
    assert issubclass(sdk.WorkflowExtension, sdk.Extension)
    assert issubclass(sdk.RepositoryExtension, sdk.Extension)
    assert issubclass(sdk.MCPToolExtension, sdk.Extension)
