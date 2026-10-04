"""Internal OpenAI-only composition root for one exact-bound invocation adapter."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import TypeGuard

from manga_director.production.next_generation_openai_private_credentials import (
    ExactKeySecretManager,
    OpenAIPrivateCredentialResolver,
)
from manga_director.production.next_generation_openai_provider_adapter import (
    OpenAIImageClientFactoryPort,
    OpenAIImagePrivateTransport,
)
from manga_director.production.next_generation_provider_adapter_composition import (
    BoundProviderGenerationInvocationAdapter,
    ProviderAdapterCompositionService,
)
from manga_director.production.next_generation_provider_configuration import (
    ProviderConfigurationNormalizationReport,
)
from manga_director.production.next_generation_provider_output_configuration import (
    ProviderOutputConfigurationBindingReport,
)
from manga_director.security import CredentialManager

_SELECTOR = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
SecretLookup = Callable[[str], str | None]


def compose_openai_private_invocation_adapter(
    selector: str | None,
    provider_configuration_normalization_report: ProviderConfigurationNormalizationReport,
    provider_output_configuration_binding_report: ProviderOutputConfigurationBindingReport,
    *,
    secret_lookup: SecretLookup | None = None,
    client_factory: OpenAIImageClientFactoryPort | None = None,
) -> BoundProviderGenerationInvocationAdapter | None:
    """Compose one private OpenAI adapter without resolving a credential yet."""

    if not _is_valid_selector(selector):
        return None
    if not _reports_are_exact_ready_pair(
        provider_configuration_normalization_report,
        provider_output_configuration_binding_report,
    ):
        return None

    secret_manager = ExactKeySecretManager(selector, secret_lookup)
    resolver = OpenAIPrivateCredentialResolver(CredentialManager(secret_manager), selector)
    transport = OpenAIImagePrivateTransport(
        resolver,
        provider_output_configuration_binding_report,
        client_factory,
    )
    return ProviderAdapterCompositionService().compose(
        provider_configuration_normalization_report,
        transport,
    )


def _is_valid_selector(selector: str | None) -> TypeGuard[str]:
    return isinstance(selector, str) and bool(_SELECTOR.fullmatch(selector))


def _reports_are_exact_ready_pair(
    configuration: ProviderConfigurationNormalizationReport,
    output_configuration: ProviderOutputConfigurationBindingReport,
) -> bool:
    selection = configuration.selection
    output = output_configuration.output_configuration
    return bool(
        configuration.status == "ready"
        and configuration.ready is True
        and selection is not None
        and output_configuration.status == "ready"
        and output_configuration.ready is True
        and output is not None
        and output_configuration.provider_configuration_normalization_report == configuration
        and output.attempt_id == selection.attempt_id
        and output.provider_reference == selection.provider_reference
        and output.profile_id == selection.profile_id
        and output.profile_version == selection.profile_version
        and selection.model_id.availability == "known"
        and output.model_id == selection.model_id.value
    )
