"""Internal OpenAI output handoff to an injected asset-owner sink.

The generic asset-registration service retains the output handle as opaque.
Only this provider-private adapter may unwrap OpenAI's in-memory image
material before passing it to an injected owner boundary.  It never chooses an
asset identifier, retains bytes, accesses storage, or constructs evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from manga_director.production.next_generation_asset_registration import (
    AssetRegistrationPort,
    AssetRegistrationRequest,
    AssetRegistrationRuntimeResult,
)
from manga_director.production.next_generation_local_durable_asset_owner import (
    OwnerRegistrationMaterial,
    ProviderNeutralAssetOwner,
)
from manga_director.production.next_generation_openai_provider_adapter import (
    OpenAIInMemoryGeneratedImageMaterial,
)

_OPENAI_MEDIA_TYPE = "image/png"


@dataclass(frozen=True, slots=True)
class OpenAIOutputAssetRegistrationRequest:
    """Runtime-only OpenAI material for one owner-controlled registration."""

    attempt_id: str
    provider_reference: str
    image_bytes: bytes = field(repr=False, compare=False)
    media_type_hint: str = _OPENAI_MEDIA_TYPE


class AssetOwnerSink(Protocol):
    """Provider-private owner boundary for durable output registration."""

    def register(
        self, request: OpenAIOutputAssetRegistrationRequest
    ) -> AssetRegistrationRuntimeResult: ...


class OpenAIAssetOwnerSinkBridge(AssetOwnerSink):
    """Translate OpenAI-private material into a provider-neutral owner request."""

    def __init__(self, asset_owner: ProviderNeutralAssetOwner) -> None:
        self._asset_owner = asset_owner

    def register(
        self, request: OpenAIOutputAssetRegistrationRequest
    ) -> AssetRegistrationRuntimeResult:
        return self._asset_owner.register(
            OwnerRegistrationMaterial(
                attempt_id=request.attempt_id,
                provider_reference=request.provider_reference,
                image_bytes=request.image_bytes,
                media_type=request.media_type_hint,
            )
        )


class OpenAIOutputAssetRegistrationAdapter(AssetRegistrationPort):
    """Pass only valid OpenAI in-memory material to a configured owner sink."""

    def __init__(self, asset_owner_sink: AssetOwnerSink) -> None:
        self._asset_owner_sink = asset_owner_sink

    def register(self, request: AssetRegistrationRequest) -> AssetRegistrationRuntimeResult:
        """Return only an owner result; never retain private output material."""

        material: object | None = None
        image_bytes: bytes | None = None
        owner_request: OpenAIOutputAssetRegistrationRequest | None = None
        try:
            material = request.output_handle.opaque_value
            if not isinstance(material, OpenAIInMemoryGeneratedImageMaterial):
                return _failed_result(request)
            image_bytes = material.image_bytes
            if (
                not isinstance(image_bytes, bytes)
                or not image_bytes
                or material.media_type != _OPENAI_MEDIA_TYPE
            ):
                return _failed_result(request)
            owner_request = OpenAIOutputAssetRegistrationRequest(
                attempt_id=request.attempt_id,
                provider_reference=request.provider_reference,
                image_bytes=image_bytes,
                media_type_hint=_OPENAI_MEDIA_TYPE,
            )
            return self._asset_owner_sink.register(owner_request)
        except Exception:
            return _failed_result(request)
        finally:
            # Local references are deliberately released; the caller retains its own opaque handle.
            owner_request = None
            image_bytes = None
            material = None


def _failed_result(request: AssetRegistrationRequest) -> AssetRegistrationRuntimeResult:
    return AssetRegistrationRuntimeResult(
        attempt_id=request.attempt_id,
        provider_reference=request.provider_reference,
        outcome="failed",
    )
