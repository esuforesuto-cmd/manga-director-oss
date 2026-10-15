"""Focused tests for ComfyUI output handoff to the asset-owner boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import pytest

from manga_director.production.next_generation_asset_registration import (
    AssetRegistrationRequest,
    AssetRegistrationRuntimeResult,
)
from manga_director.production.next_generation_comfyui_output_asset_registration import (
    ComfyUIAssetOwnerSink,
    ComfyUIOutputAssetRegistrationAdapter,
    ComfyUIOutputAssetRegistrationRequest,
)
from manga_director.production.next_generation_comfyui_provider_adapter import (
    ComfyUIInMemoryGeneratedImageMaterial,
)
from manga_director.production.next_generation_provider_invocation import (
    OpaqueGeneratedOutputHandle,
)

_ATTEMPT_ID = "attempt:v7-04:001"
_PROVIDER_REFERENCE = "provider:comfyui"
_PNG = b"\x89PNG\r\n\x1a\nprivate-test-material"


@dataclass
class _Sink(ComfyUIAssetOwnerSink):
    calls: list[ComfyUIOutputAssetRegistrationRequest]
    raises: bool = False

    def register(
        self, request: ComfyUIOutputAssetRegistrationRequest
    ) -> AssetRegistrationRuntimeResult:
        self.calls.append(request)
        if self.raises:
            raise RuntimeError("private owner detail")
        return AssetRegistrationRuntimeResult(
            attempt_id=request.attempt_id,
            provider_reference=request.provider_reference,
            outcome="registered",
            durable_registration_confirmed=True,
        )


def _request(material: object) -> AssetRegistrationRequest:
    return AssetRegistrationRequest(
        attempt_id=_ATTEMPT_ID,
        provider_reference=_PROVIDER_REFERENCE,
        output_handle=OpaqueGeneratedOutputHandle(material),
    )


def test_validated_comfyui_material_crosses_owner_boundary_once() -> None:
    sink = _Sink([])
    adapter = ComfyUIOutputAssetRegistrationAdapter(sink)

    result = adapter.register(
        _request(ComfyUIInMemoryGeneratedImageMaterial(image_bytes=_PNG))
    )

    assert result.outcome == "registered"
    assert len(sink.calls) == 1
    assert sink.calls[0].attempt_id == _ATTEMPT_ID
    assert sink.calls[0].provider_reference == _PROVIDER_REFERENCE
    assert sink.calls[0].media_type_hint == "image/png"
    assert sink.calls[0].image_bytes == _PNG


@pytest.mark.parametrize(
    "material",
    (
        None,
        object(),
        ComfyUIInMemoryGeneratedImageMaterial(image_bytes=b""),
        ComfyUIInMemoryGeneratedImageMaterial(
            image_bytes=_PNG, media_type=cast(str, "image/jpeg")
        ),
    ),
)
def test_wrong_empty_or_non_png_material_never_reaches_owner(material: object) -> None:
    sink = _Sink([])
    result = ComfyUIOutputAssetRegistrationAdapter(sink).register(_request(material))

    assert result.outcome == "failed"
    assert sink.calls == []


def test_owner_exception_is_redacted_and_adapter_retains_no_bytes() -> None:
    sink = _Sink([], raises=True)
    adapter = ComfyUIOutputAssetRegistrationAdapter(sink)
    result = adapter.register(
        _request(ComfyUIInMemoryGeneratedImageMaterial(image_bytes=_PNG))
    )

    assert result.outcome == "failed"
    assert "private owner detail" not in repr(result)
    assert not any("image" in name or "byte" in name for name in vars(adapter))
