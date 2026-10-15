"""Internal ComfyUI byte handoff to the existing provider-neutral asset owner."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from manga_director.production.next_generation_asset_registration import (
    AssetRegistrationPort,
    AssetRegistrationRequest,
    AssetRegistrationRuntimeResult,
)
from manga_director.production.next_generation_comfyui_provider_adapter import (
    ComfyUIInMemoryGeneratedImageMaterial,
)
from manga_director.production.next_generation_local_durable_asset_owner import (
    OwnerRegistrationMaterial,
    ProviderNeutralAssetOwner,
)

_COMFYUI_MEDIA_TYPE = "image/png"


@dataclass(frozen=True, slots=True)
class ComfyUIOutputAssetRegistrationRequest:
    """Runtime-only ComfyUI material for one owner-controlled registration."""

    attempt_id: str
    provider_reference: str
    image_bytes: bytes = field(repr=False, compare=False)
    media_type_hint: str = _COMFYUI_MEDIA_TYPE


class ComfyUIAssetOwnerSink(Protocol):
    def register(
        self, request: ComfyUIOutputAssetRegistrationRequest
    ) -> AssetRegistrationRuntimeResult: ...


class ComfyUIAssetOwnerSinkBridge(ComfyUIAssetOwnerSink):
    def __init__(self, asset_owner: ProviderNeutralAssetOwner) -> None:
        self._asset_owner = asset_owner

    def register(
        self, request: ComfyUIOutputAssetRegistrationRequest
    ) -> AssetRegistrationRuntimeResult:
        return self._asset_owner.register(
            OwnerRegistrationMaterial(
                attempt_id=request.attempt_id,
                provider_reference=request.provider_reference,
                image_bytes=request.image_bytes,
                media_type=request.media_type_hint,
            )
        )


class ComfyUIOutputAssetRegistrationAdapter(AssetRegistrationPort):
    """Unwrap only the validated in-memory ComfyUI PNG material."""

    def __init__(self, asset_owner_sink: ComfyUIAssetOwnerSink) -> None:
        self._asset_owner_sink = asset_owner_sink

    def register(self, request: AssetRegistrationRequest) -> AssetRegistrationRuntimeResult:
        material: object | None = None
        image_bytes: bytes | None = None
        owner_request: ComfyUIOutputAssetRegistrationRequest | None = None
        try:
            material = request.output_handle.opaque_value
            if not isinstance(material, ComfyUIInMemoryGeneratedImageMaterial):
                return _failed_result(request)
            image_bytes = material.image_bytes
            if (
                not isinstance(image_bytes, bytes)
                or not image_bytes
                or material.media_type != _COMFYUI_MEDIA_TYPE
            ):
                return _failed_result(request)
            owner_request = ComfyUIOutputAssetRegistrationRequest(
                attempt_id=request.attempt_id,
                provider_reference=request.provider_reference,
                image_bytes=image_bytes,
            )
            return self._asset_owner_sink.register(owner_request)
        except Exception:
            return _failed_result(request)
        finally:
            owner_request = None
            image_bytes = None
            material = None


def _failed_result(request: AssetRegistrationRequest) -> AssetRegistrationRuntimeResult:
    return AssetRegistrationRuntimeResult(
        attempt_id=request.attempt_id,
        provider_reference=request.provider_reference,
        outcome="failed",
    )
