"""Private V7-13 Panel adapter over the existing V7-04 ComfyUI transport."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from manga_director.production.future_real_delivery_i01 import (
    StrictPngStructuralValidatorV1,
)
from manga_director.production.next_generation_comfyui_fixed_workflow import (
    validate_comfyui_checkpoint_name,
)
from manga_director.production.next_generation_comfyui_provider_adapter import (
    ComfyUIHttpClientPort,
    ComfyUIImagePrivateTransport,
    ComfyUIInMemoryGeneratedImageMaterial,
)
from manga_director.production.next_generation_local_durable_asset_owner import (
    LocalDurableAssetOwner,
    OwnerRegistrationMaterial,
)
from manga_director.production.next_generation_panel_execution_attempt import (
    PanelAttemptReservation,
    PanelGenerationRequest,
)
from manga_director.production.next_generation_panel_generation_evidence import (
    PanelAsset,
    PanelGenerationEvidence,
)
from manga_director.production.next_generation_provider_adapter_composition import (
    ProviderPrivateTransportRequest,
    ProviderPrivateTransportResult,
)
from manga_director.production.next_generation_provider_output_configuration import (
    ProviderOutputConfigurationBindingReport,
)
from manga_director.workflow.localfile_panel_aware_page_generation import (
    PanelProviderExecution,
)

_PROVIDER_REFERENCE = "provider-comfyui-v7-014"
_PROVIDER_ID = "comfyui"
_PROFILE_ID = "profile:v7-04:prompt-only-png"
_PROFILE_VERSION = "v1"
_WORKFLOW_ID = "workflow:v7-04:fixed-core-png"
_WORKFLOW_VERSION = "v1"
_MODEL_VERSION = "local-checkpoint"
_OUTPUT_SIZE = "1024x1024"
_OUTPUT_QUALITY = "medium"


class _TransportPort(Protocol):
    def preflight(self) -> None: ...

    def prepare(
        self, request: ProviderPrivateTransportRequest
    ) -> Callable[[], ProviderPrivateTransportResult] | None: ...


ConfigurationReportFactory = Callable[
    [PanelGenerationRequest, PanelAttemptReservation, str],
    ProviderOutputConfigurationBindingReport | None,
]
TransportFactory = Callable[[str, ProviderOutputConfigurationBindingReport], _TransportPort]


class LocalFileComfyUIPanelProvider:
    """Prepare one exact Panel request, then submit it once after durable start."""

    def __init__(
        self,
        *,
        checkpoint_name: str,
        owner_root: Path,
        configuration_report_factory: ConfigurationReportFactory,
        http_client: ComfyUIHttpClientPort | None = None,
        transport_factory: TransportFactory | None = None,
    ) -> None:
        self._checkpoint_name = validate_comfyui_checkpoint_name(checkpoint_name)
        self._owner_root = owner_root
        self._configuration_report_factory = configuration_report_factory
        self._http_client = http_client
        self._transport_factory = transport_factory or self._default_transport
        self._registration = LocalDurableAssetOwner(owner_root, _issue_i02_commitment=False)

    def prepare(
        self, request: PanelGenerationRequest, reservation: PanelAttemptReservation
    ) -> Callable[[], PanelProviderExecution] | None:
        """Run only bounded read-only preflight and transport preparation."""

        raw_prompt = _raw_prompt(request)
        if raw_prompt is None or not _request_matches_reservation(request, reservation):
            return None
        try:
            configuration = self._configuration_report_factory(
                request, reservation, self._checkpoint_name
            )
            if configuration is None or not _configuration_matches(
                configuration, request, reservation, self._checkpoint_name
            ):
                return None
            provider_configuration_fingerprint = _configuration_fingerprint(
                reservation, self._checkpoint_name
            )
            asset_id = _derived_asset_id(request, reservation, self._checkpoint_name)
            evidence_id = _derived_evidence_id(reservation, asset_id)
            transport = self._transport_factory(self._checkpoint_name, configuration)
            selection = configuration.provider_configuration_normalization_report.selection
            if selection is None:
                return None
            private_request = ProviderPrivateTransportRequest(
                attempt_id=reservation.attempt_id,
                provider_reference=_PROVIDER_REFERENCE,
                profile_id=_PROFILE_ID,
                profile_version=_PROFILE_VERSION,
                configuration_selection=selection,
                raw_prompt=raw_prompt,
            )
            transport.preflight()
            prepared = transport.prepare(private_request)
        except Exception:
            return None
        if prepared is None:
            return None

        def invoke_prepared() -> PanelProviderExecution:
            try:
                result = prepared()
                if (
                    not isinstance(result, ProviderPrivateTransportResult)
                    or result.outcome != "succeeded"
                ):
                    return PanelProviderExecution("recovery_required")
                material = result.output_material
                if not isinstance(material, ComfyUIInMemoryGeneratedImageMaterial):
                    return PanelProviderExecution("recovery_required")
                return self._capture_success(
                    request,
                    reservation,
                    material,
                    asset_id,
                    evidence_id,
                    provider_configuration_fingerprint,
                )
            except Exception:
                return PanelProviderExecution("recovery_required")

        return invoke_prepared

    def invoke(
        self, request: PanelGenerationRequest, reservation: PanelAttemptReservation
    ) -> PanelProviderExecution:
        """Fail closed: the ComfyUI adapter never bypasses pre-start preparation."""

        del request, reservation
        return PanelProviderExecution("recovery_required")

    def read(self, asset: PanelAsset) -> bytes | None:
        """Read the exact registered backing bytes through V7-04's verified owner."""

        try:
            inventory = LocalDurableAssetOwner.observe_attempts(
                self._owner_root, (asset.attempt_id,)
            )
            if inventory.outcome != "found" or len(inventory.bindings) != 1:
                return None
            binding = inventory.bindings[0]
            if (
                binding.attempt_id != asset.attempt_id
                or binding.output_asset_id != asset.asset_id
                or binding.provider_reference != _PROVIDER_REFERENCE
                or binding.media_type != "image/png"
                or binding.content_sha256 != asset.content_sha256
            ):
                return None
            owner = LocalDurableAssetOwner._open_existing_for_presentation(self._owner_root)
            lease = owner._read_verified_presentation_bytes(
                attempt_id=asset.attempt_id,
                provider_reference=_PROVIDER_REFERENCE,
                output_asset_id=binding.output_asset_id,
                expected_sha256=asset.content_sha256,
                expected_media_type="image/png",
            )
            try:
                return lease.image_bytes
            finally:
                lease.release()
        except Exception:
            return None

    def _capture_success(
        self,
        request: PanelGenerationRequest,
        reservation: PanelAttemptReservation,
        material: ComfyUIInMemoryGeneratedImageMaterial,
        asset_id: str,
        evidence_id: str,
        provider_configuration_fingerprint: str,
    ) -> PanelProviderExecution:
        image_bytes = material.image_bytes
        if material.media_type != "image/png":
            return PanelProviderExecution("recovery_required")
        info = StrictPngStructuralValidatorV1().validate(image_bytes)
        if info.width != 1024 or info.height != 1024:
            return PanelProviderExecution("recovery_required")
        output_sha256 = hashlib.sha256(image_bytes).hexdigest()
        registered = self._registration._register_v714_panel_asset(
            OwnerRegistrationMaterial(
                attempt_id=reservation.attempt_id,
                provider_reference=_PROVIDER_REFERENCE,
                image_bytes=image_bytes,
                media_type=material.media_type,
            ),
            asset_id,
        )
        output = registered.output
        if (
            registered.outcome != "registered"
            or registered.attempt_id != reservation.attempt_id
            or registered.provider_reference != _PROVIDER_REFERENCE
            or output is None
            or output.output_content_hash is None
            or output.output_content_hash.availability != "known"
            or output.output_content_hash.value != output_sha256
            or output.output_asset_id != asset_id
            or output.media_type != "image/png"
            or registered.durable_registration_confirmed is not True
        ):
            return PanelProviderExecution("recovery_required")
        asset = PanelAsset(
            asset_id=asset_id,
            plan_id=request.plan_id,
            plan_fingerprint=request.plan_fingerprint,
            project_id=request.project_id,
            page_id=request.page_id,
            panel_id=request.panel_id,
            panel_order=request.panel_order,
            request_id=request.request_id,
            request_fingerprint=request.request_fingerprint or "",
            attempt_id=reservation.attempt_id,
            width=info.width,
            height=info.height,
            content_sha256=output_sha256,
        )
        evidence = PanelGenerationEvidence(
            evidence_id=evidence_id,
            plan_id=request.plan_id,
            plan_fingerprint=request.plan_fingerprint,
            project_id=request.project_id,
            page_id=request.page_id,
            panel_id=request.panel_id,
            panel_order=request.panel_order,
            request_id=request.request_id,
            request_fingerprint=request.request_fingerprint or "",
            attempt_id=reservation.attempt_id,
            input_reference=request.input_reference,
            input_sha256=request.input_sha256,
            provider_reference=_PROVIDER_REFERENCE,
            provider_configuration_fingerprint=provider_configuration_fingerprint,
            provenance_reference=request.provenance_reference,
            output_asset_id=asset_id,
            output_sha256=output_sha256,
            media_type="image/png",
            width=info.width,
            height=info.height,
            outcome="accepted",
            attempt_state="PANEL_ACCEPTED",
        )
        return PanelProviderExecution("succeeded", asset, evidence, image_bytes)

    def _default_transport(
        self,
        checkpoint_name: str,
        configuration: ProviderOutputConfigurationBindingReport,
    ) -> ComfyUIImagePrivateTransport:
        return ComfyUIImagePrivateTransport(
            checkpoint_name, configuration, http_client=self._http_client
        )


def _raw_prompt(request: PanelGenerationRequest) -> str | None:
    prompt = request.panel_prompt
    value = {
        "action": prompt.action,
        "background": prompt.background,
        "character_identities": list(prompt.character_identities),
        "composition": prompt.composition,
        "constraints": list(prompt.constraints),
        "continuity_bindings": list(prompt.continuity_bindings),
        "narrative_intent": prompt.narrative_intent,
    }
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return (
        raw
        if request.capability_requirements == ("text-prompt", "png-output")
        and request.input_reference == f"input-v7-014-{digest}"
        and digest == request.input_sha256
        else None
    )


def _request_matches_reservation(
    request: PanelGenerationRequest, reservation: PanelAttemptReservation
) -> bool:
    return bool(
        request.plan_id == reservation.plan_id
        and request.plan_fingerprint == reservation.plan_fingerprint
        and request.project_id == reservation.project_id
        and request.page_id == reservation.page_id
        and request.panel_id == reservation.panel_id
        and request.panel_order == reservation.panel_order
        and request.request_id == reservation.request_id
        and request.request_fingerprint == reservation.request_fingerprint
        and reservation.provider_reference == _PROVIDER_REFERENCE
        and reservation.attempt_id
        == _prefixed_digest(
            "attempt-v7-014-",
            {
                "kind": "panel_attempt_v1",
                "version": 1,
                "request_fingerprint": request.request_fingerprint,
                "provider_reference": _PROVIDER_REFERENCE,
                "authorization_reference": reservation.authorization_reference,
            },
        )
    )


def _configuration_matches(
    report: ProviderOutputConfigurationBindingReport | None,
    request: PanelGenerationRequest,
    reservation: PanelAttemptReservation,
    checkpoint_name: str,
) -> bool:  # noqa: C901 - all provider configuration bindings remain visible
    if report is None or report.status != "ready" or report.ready is not True:
        return False
    normalized = report.provider_configuration_normalization_report
    selection = normalized.selection
    output = report.output_configuration
    authorization = normalized.authorized_execution_envelope_validation_report
    execution_authorization = authorization.execution_authorization_validation_report
    envelopes = authorization.envelopes
    authorization_records = execution_authorization.authorizations
    if (
        normalized.status != "ready"
        or normalized.ready is not True
        or authorization.status != "ready"
        or authorization.ready is not True
        or execution_authorization.status != "ready"
        or execution_authorization.ready is not True
        or len(authorization_records) != 1
        or authorization_records[0].authorization_id != reservation.authorization_reference
        or authorization_records[0].request_id != request.request_id
        or authorization_records[0].provider_reference != _PROVIDER_REFERENCE
        or len(envelopes) != 1
        or envelopes[0].attempt_id != reservation.attempt_id
        or envelopes[0].provider_reference != _PROVIDER_REFERENCE
        or envelopes[0].authorization_ids != (reservation.authorization_reference,)
        or envelopes[0].request_id != request.request_id
        or envelopes[0].profile_id != _PROFILE_ID
        or envelopes[0].profile_version != _PROFILE_VERSION
        or envelopes[0].input_reference != request.input_reference
        or selection is None
        or output is None
        or selection.attempt_id != reservation.attempt_id
        or selection.provider_reference != _PROVIDER_REFERENCE
        or selection.profile_id != _PROFILE_ID
        or selection.profile_version != _PROFILE_VERSION
        or selection.provider_id.availability != "known"
        or selection.provider_id.value != _PROVIDER_ID
        or selection.model_id.availability != "known"
        or selection.model_id.value != checkpoint_name
        or selection.model_version.availability != "known"
        or selection.model_version.value != _MODEL_VERSION
        or selection.workflow_id.availability != "known"
        or selection.workflow_id.value != _WORKFLOW_ID
        or selection.workflow_version.availability != "known"
        or selection.workflow_version.value != _WORKFLOW_VERSION
        or selection.preset_id is not None
        or selection.preset_version is not None
        or selection.requested_seed is None
        or selection.requested_seed.availability != "known"
        or selection.requested_seed.value != "derived-from-attempt"
        or output.attempt_id != reservation.attempt_id
        or output.provider_reference != _PROVIDER_REFERENCE
        or output.profile_id != _PROFILE_ID
        or output.profile_version != _PROFILE_VERSION
        or output.model_id != checkpoint_name
        or output.output_size != _OUTPUT_SIZE
        or output.output_quality != _OUTPUT_QUALITY
        or request.request_fingerprint != reservation.request_fingerprint
    ):
        return False
    expected_config = _configuration_fingerprint(reservation, checkpoint_name)
    expected_execution = _prefixed_digest(
        "",
        {
            "kind": "panel_execution_v1",
            "version": 1,
            "attempt_id": reservation.attempt_id,
            "request_fingerprint": request.request_fingerprint,
            "provider_reference": _PROVIDER_REFERENCE,
            "authorization_reference": reservation.authorization_reference,
            "provider_configuration_fingerprint": expected_config,
        },
    )
    return reservation.execution_fingerprint == expected_execution


def _configuration_fingerprint(reservation: PanelAttemptReservation, checkpoint_name: str) -> str:
    return _digest(
        {
            "kind": "provider_configuration_v1",
            "version": 1,
            "attempt_id": reservation.attempt_id,
            "provider_reference": _PROVIDER_REFERENCE,
            "provider_id": _PROVIDER_ID,
            "model_id": checkpoint_name,
            "model_version": _MODEL_VERSION,
            "profile_id": _PROFILE_ID,
            "profile_version": _PROFILE_VERSION,
            "workflow_id": _WORKFLOW_ID,
            "workflow_version": _WORKFLOW_VERSION,
            "preset_id": None,
            "preset_version": None,
            "requested_seed": "derived-from-attempt",
            "output_size": _OUTPUT_SIZE,
            "output_quality": _OUTPUT_QUALITY,
        }
    )


def _derived_asset_id(
    request: PanelGenerationRequest,
    reservation: PanelAttemptReservation,
    checkpoint_name: str,
) -> str:
    return _prefixed_digest(
        "panel-asset-v7-014-",
        {
            "kind": "panel_asset_id_v1",
            "version": 1,
            "attempt_id": reservation.attempt_id,
            "request_fingerprint": request.request_fingerprint,
            "execution_fingerprint": reservation.execution_fingerprint,
            "input_sha256": request.input_sha256,
            "provider_configuration_fingerprint": _configuration_fingerprint(
                reservation, checkpoint_name
            ),
            "provenance_reference": request.provenance_reference,
            "media_type": "image/png",
        },
    )


def _derived_evidence_id(reservation: PanelAttemptReservation, asset_id: str) -> str:
    return _prefixed_digest(
        "panel-evidence-v7-014-",
        {
            "kind": "panel_evidence_id_v1",
            "version": 1,
            "attempt_id": reservation.attempt_id,
            "request_fingerprint": reservation.request_fingerprint,
            "execution_fingerprint": reservation.execution_fingerprint,
            "asset_id": asset_id,
        },
    )


def _prefixed_digest(prefix: str, value: object) -> str:
    return prefix + _digest(value)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
