from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from manga_director.production.next_generation_authorized_execution_envelope import (
    AuthorizedGenerationExecutionEnvelopeDTO,
    AuthorizedGenerationExecutionEnvelopeValidationReport,
)
from manga_director.production.next_generation_comfyui_provider_adapter import (
    ComfyUIImagePrivateTransport,
    ComfyUIInMemoryGeneratedImageMaterial,
)
from manga_director.production.next_generation_deterministic_page_compositor import (
    encode_rgb_png,
)
from manga_director.production.next_generation_execution_authorization import (
    ExecutionAuthorizationRecordDTO,
    ExecutionAuthorizationValidationReport,
)
from manga_director.production.next_generation_generation_evidence import (
    EvidenceValueDTO,
)
from manga_director.production.next_generation_page_generation_plan import (
    PageGenerationPlan,
    PagePanelSpecification,
    PanelRectangle,
)
from manga_director.production.next_generation_panel_execution_attempt import (
    PanelAttemptReservation,
    PanelGenerationRequest,
)
from manga_director.production.next_generation_provider_adapter_composition import (
    ProviderPrivateTransportResult,
)
from manga_director.production.next_generation_provider_configuration import (
    ProviderConfigurationNormalizationReport,
    ProviderConfigurationSelectionDTO,
)
from manga_director.production.next_generation_provider_output_configuration import (
    ProviderOutputConfigurationBindingDTO,
    ProviderOutputConfigurationBindingReport,
)
from manga_director.workflow import localfile_comfyui_panel_provider as panel_provider_module
from manga_director.workflow.localfile_comfyui_panel_provider import (
    LocalFileComfyUIPanelProvider,
)

_PROVIDER_REFERENCE = "provider-comfyui-v7-014"
_PROFILE_ID = "profile:v7-04:prompt-only-png"
_PROFILE_VERSION = "v1"


class _PreparedTransport:
    def __init__(
        self,
        image_bytes: bytes,
        events: list[str],
        result_override: object | None = None,
    ) -> None:
        self.image_bytes = image_bytes
        self.events = events
        self.result_override = result_override
        self.request = None

    def preflight(self) -> None:
        self.events.append("preflight")

    def prepare(self, request):  # type: ignore[no-untyped-def]
        self.events.append("prepare")
        self.request = request
        return lambda: self._invoke()

    def _invoke(self) -> object:
        self.events.append("submit")
        if self.result_override is not None:
            return self.result_override
        return ProviderPrivateTransportResult(
            "succeeded",
            ComfyUIInMemoryGeneratedImageMaterial(self.image_bytes),
        )


class _FakeComfyUIHttpClient:
    origin = "http://127.0.0.1:8188"

    def __init__(self, image_bytes: bytes) -> None:
        self.image_bytes = image_bytes
        self.calls: list[str] = []
        self.submitted: dict[str, object] | None = None

    def get_json(self, path: str) -> object:
        self.calls.append(f"GET {path}")
        if path == "/system_stats":
            return {"system": {"comfyui_version": "fake"}}
        if path.startswith("/object_info/"):
            node_type = path.rsplit("/", 1)[-1]
            info: dict[str, object] = {"python_module": "nodes", "input": {"required": {}}}
            if node_type == "CheckpointLoaderSimple":
                info["input"] = {"required": {"ckpt_name": [["test-checkpoint.safetensors"], {}]}}
            return {node_type: info}
        if path == "/history/fake-prompt":
            return {
                "fake-prompt": {
                    "status": {"status_str": "success", "completed": True},
                    "outputs": {
                        "7": {
                            "images": [
                                {
                                    "filename": "result.png",
                                    "subfolder": "",
                                    "type": "output",
                                }
                            ]
                        }
                    },
                }
            }
        raise AssertionError(f"unexpected fake GET path: {path}")

    def post_json(self, path: str, payload: object) -> object:
        assert path == "/prompt"
        assert isinstance(payload, dict)
        self.calls.append("POST /prompt")
        self.submitted = payload
        return {"prompt_id": "fake-prompt", "node_errors": {}}

    def get_png(self, path: str, query: object) -> bytes:
        assert path == "/view"
        self.calls.append("GET /view")
        return self.image_bytes


def _operation_inputs() -> tuple[PanelGenerationRequest, PanelAttemptReservation, str]:
    source_binding_sha256 = "e" * 64
    plan_id = f"plan-v7-014-{source_binding_sha256}"
    panel_id = "panel-v7-014-" + _digest(
        {
            "kind": "panel_id_v1",
            "version": 1,
            "source_binding_sha256": source_binding_sha256,
            "panel_order": 1,
        }
    )
    panel = PagePanelSpecification(
        panel_id=panel_id,
        order=1,
        rectangle=PanelRectangle(left=46875, top=31250, right=953125, bottom=968750),
        narrative_intent="The detective discovers the hidden mechanism.",
        character_identities=("detective-v1",),
        continuity_bindings=("blue-coat",),
        action="The detective points at the hidden mechanism.",
        background="A quiet archive room at night, 夜明け.",
        composition="Medium shot with the detective on the left.",
        constraints=("No lettering",),
    )
    prompt_object = {
        "action": panel.action,
        "background": panel.background,
        "character_identities": list(panel.character_identities),
        "composition": panel.composition,
        "constraints": list(panel.constraints),
        "continuity_bindings": list(panel.continuity_bindings),
        "narrative_intent": panel.narrative_intent,
    }
    raw_prompt = json.dumps(
        prompt_object, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    input_sha256 = hashlib.sha256(raw_prompt.encode("utf-8")).hexdigest()
    plan = PageGenerationPlan(
        plan_id=plan_id,
        project_id="project-test",
        page_id="page-test",
        page_number=1,
        storyboard_reference="storyboard-test",
        storyboard_sha256="a" * 64,
        prompt_built_reference="prompt-test",
        prompt_built_sha256="b" * 64,
        panel_count=1,
        panels=(panel,),
    )
    provenance_object = {
        "kind": "panel_provenance_v1",
        "version": 1,
        "source_binding_sha256": source_binding_sha256,
        "plan_id": plan.plan_id,
        "plan_fingerprint": plan.plan_fingerprint,
        "panel_id": panel.panel_id,
        "panel_order": panel.order,
    }
    provenance_reference = "panel-provenance-v7-014-" + _digest(provenance_object)
    request_object = {
        "kind": "panel_request_v1",
        "version": 1,
        "plan_id": plan.plan_id,
        "plan_fingerprint": plan.plan_fingerprint,
        "project_id": plan.project_id,
        "page_id": plan.page_id,
        "panel_id": panel.panel_id,
        "panel_order": panel.order,
        "panel_prompt": panel.model_dump(mode="json"),
        "capability_requirements": ["text-prompt", "png-output"],
        "input_reference": f"input-v7-014-{input_sha256}",
        "input_sha256": input_sha256,
        "provenance_reference": provenance_reference,
    }
    request_id = "request-v7-014-" + _digest(request_object)
    request = PanelGenerationRequest(
        request_id=request_id,
        plan_id=plan.plan_id,
        plan_fingerprint=plan.plan_fingerprint or "",
        project_id=plan.project_id,
        page_id=plan.page_id,
        panel_id=panel.panel_id,
        panel_order=1,
        panel_prompt=panel,
        capability_requirements=("text-prompt", "png-output"),
        input_reference=f"input-v7-014-{input_sha256}",
        input_sha256=input_sha256,
        provenance_reference=provenance_reference,
    )
    attempt_id = _digest(
        {
            "kind": "panel_attempt_v1",
            "version": 1,
            "request_fingerprint": request.request_fingerprint,
            "provider_reference": _PROVIDER_REFERENCE,
            "authorization_reference": "authorization-test",
        }
    )
    attempt_id = f"attempt-v7-014-{attempt_id}"
    configuration_fingerprint = _digest(
        {
            "kind": "provider_configuration_v1",
            "version": 1,
            "attempt_id": attempt_id,
            "provider_reference": _PROVIDER_REFERENCE,
            "provider_id": "comfyui",
            "model_id": "test-checkpoint.safetensors",
            "model_version": "local-checkpoint",
            "profile_id": _PROFILE_ID,
            "profile_version": _PROFILE_VERSION,
            "workflow_id": "workflow:v7-04:fixed-core-png",
            "workflow_version": "v1",
            "preset_id": None,
            "preset_version": None,
            "requested_seed": "derived-from-attempt",
            "output_size": "1024x1024",
            "output_quality": "medium",
        }
    )
    execution_fingerprint = _digest(
        {
            "kind": "panel_execution_v1",
            "version": 1,
            "attempt_id": attempt_id,
            "request_fingerprint": request.request_fingerprint,
            "provider_reference": _PROVIDER_REFERENCE,
            "authorization_reference": "authorization-test",
            "provider_configuration_fingerprint": configuration_fingerprint,
        }
    )
    reservation = PanelAttemptReservation(
        attempt_id=attempt_id,
        plan_id=plan.plan_id,
        plan_fingerprint=plan.plan_fingerprint or "",
        project_id=plan.project_id,
        page_id=plan.page_id,
        panel_id=panel.panel_id,
        panel_order=1,
        request_id=request.request_id,
        request_fingerprint=request.request_fingerprint or "",
        provider_reference=_PROVIDER_REFERENCE,
        authorization_reference="authorization-test",
        execution_fingerprint=execution_fingerprint,
    )
    return request, reservation, raw_prompt


def _configuration_report(
    request: PanelGenerationRequest,
    reservation: PanelAttemptReservation,
    checkpoint_name: str,
) -> ProviderOutputConfigurationBindingReport:
    selection = ProviderConfigurationSelectionDTO(
        attempt_id=reservation.attempt_id,
        provider_reference=_PROVIDER_REFERENCE,
        profile_id=_PROFILE_ID,
        profile_version=_PROFILE_VERSION,
        provider_id=EvidenceValueDTO(availability="known", value="comfyui"),
        model_id=EvidenceValueDTO(availability="known", value=checkpoint_name),
        model_version=EvidenceValueDTO(availability="known", value="local-checkpoint"),
        workflow_id=EvidenceValueDTO(availability="known", value="workflow:v7-04:fixed-core-png"),
        workflow_version=EvidenceValueDTO(availability="known", value="v1"),
        requested_seed=EvidenceValueDTO(availability="known", value="derived-from-attempt"),
    )
    authorization_record = ExecutionAuthorizationRecordDTO(
        authorization_id=reservation.authorization_reference,
        authorizer_id="authorizer-test",
        authorized_at=datetime(2026, 1, 1, tzinfo=UTC),
        request_id=request.request_id,
        provider_reference=_PROVIDER_REFERENCE,
    )
    execution_authorization = ExecutionAuthorizationValidationReport.model_construct(
        readiness_report=None,
        authorizations=(authorization_record,),
        findings=(),
        status="ready",
        ready=True,
    )
    envelope = AuthorizedGenerationExecutionEnvelopeDTO(
        attempt_id=reservation.attempt_id,
        request_id=request.request_id,
        provider_reference=_PROVIDER_REFERENCE,
        authorization_ids=(reservation.authorization_reference,),
        profile_id=_PROFILE_ID,
        profile_version=_PROFILE_VERSION,
        generation_intent_reference="intent-test",
        input_reference=request.input_reference,
    )
    authorization = AuthorizedGenerationExecutionEnvelopeValidationReport.model_construct(
        execution_authorization_validation_report=execution_authorization,
        envelopes=(envelope,),
        findings=(),
        status="ready",
        ready=True,
    )
    normalized = ProviderConfigurationNormalizationReport.model_construct(
        authorized_execution_envelope_validation_report=authorization,
        selection=selection,
        findings=(),
        status="ready",
        ready=True,
    )
    output = ProviderOutputConfigurationBindingDTO(
        attempt_id=reservation.attempt_id,
        provider_reference=_PROVIDER_REFERENCE,
        profile_id=_PROFILE_ID,
        profile_version=_PROFILE_VERSION,
        model_id=checkpoint_name,
        output_size="1024x1024",
        output_quality="medium",
    )
    return ProviderOutputConfigurationBindingReport.model_construct(
        provider_configuration_normalization_report=normalized,
        output_configuration=output,
        findings=(),
        status="ready",
        ready=True,
    )


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


def _valid_panel_png() -> bytes:
    return encode_rgb_png(1024, 1024, b"\x10\x20\x30" * (1024 * 1024))


def test_rfc_v7014_panel_provider_bindings_match_literal_golden_vectors() -> None:
    request, reservation, raw_prompt = _operation_inputs()
    panel = request.panel_prompt
    source_binding_sha256 = "e" * 64
    provider_configuration_fingerprint = (
        "4c448812f8b6d709c834cb84c39083ff3d75fbbf88868a41ef4c251796ac374c"
    )

    def canonical_json(value: object) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    panel_id_object = {
        "kind": "panel_id_v1",
        "version": 1,
        "source_binding_sha256": source_binding_sha256,
        "panel_order": 1,
    }
    raw_prompt_object = {
        "action": panel.action,
        "background": panel.background,
        "character_identities": list(panel.character_identities),
        "composition": panel.composition,
        "constraints": list(panel.constraints),
        "continuity_bindings": list(panel.continuity_bindings),
        "narrative_intent": panel.narrative_intent,
    }
    panel_prompt_object = panel.model_dump(mode="json")
    provenance_object = {
        "kind": "panel_provenance_v1",
        "version": 1,
        "source_binding_sha256": source_binding_sha256,
        "plan_id": request.plan_id,
        "plan_fingerprint": request.plan_fingerprint,
        "panel_id": request.panel_id,
        "panel_order": request.panel_order,
    }
    request_id_object = {
        "kind": "panel_request_v1",
        "version": 1,
        "plan_id": request.plan_id,
        "plan_fingerprint": request.plan_fingerprint,
        "project_id": request.project_id,
        "page_id": request.page_id,
        "panel_id": request.panel_id,
        "panel_order": request.panel_order,
        "panel_prompt": panel_prompt_object,
        "capability_requirements": list(request.capability_requirements),
        "input_reference": request.input_reference,
        "input_sha256": request.input_sha256,
        "provenance_reference": request.provenance_reference,
    }
    request_fingerprint_object = request.model_dump(mode="json", exclude={"request_fingerprint"})
    attempt_object = {
        "kind": "panel_attempt_v1",
        "version": 1,
        "request_fingerprint": request.request_fingerprint,
        "provider_reference": reservation.provider_reference,
        "authorization_reference": reservation.authorization_reference,
    }
    configuration_object = {
        "kind": "provider_configuration_v1",
        "version": 1,
        "attempt_id": reservation.attempt_id,
        "provider_reference": reservation.provider_reference,
        "provider_id": "comfyui",
        "model_id": "test-checkpoint.safetensors",
        "model_version": "local-checkpoint",
        "profile_id": _PROFILE_ID,
        "profile_version": _PROFILE_VERSION,
        "workflow_id": "workflow:v7-04:fixed-core-png",
        "workflow_version": "v1",
        "preset_id": None,
        "preset_version": None,
        "requested_seed": "derived-from-attempt",
        "output_size": "1024x1024",
        "output_quality": "medium",
    }
    execution_object = {
        "kind": "panel_execution_v1",
        "version": 1,
        "attempt_id": reservation.attempt_id,
        "request_fingerprint": request.request_fingerprint,
        "provider_reference": reservation.provider_reference,
        "authorization_reference": reservation.authorization_reference,
        "provider_configuration_fingerprint": provider_configuration_fingerprint,
    }
    asset_id_object = {
        "kind": "panel_asset_id_v1",
        "version": 1,
        "attempt_id": reservation.attempt_id,
        "request_fingerprint": request.request_fingerprint,
        "execution_fingerprint": reservation.execution_fingerprint,
        "input_sha256": request.input_sha256,
        "provider_configuration_fingerprint": provider_configuration_fingerprint,
        "provenance_reference": request.provenance_reference,
        "media_type": "image/png",
    }
    asset_id = "panel-asset-v7-014-1945138b50b82856e4146ae4883a54b6c0f835f40cb804b8facc22daba49eece"
    evidence_id_object = {
        "kind": "panel_evidence_id_v1",
        "version": 1,
        "attempt_id": reservation.attempt_id,
        "request_fingerprint": request.request_fingerprint,
        "execution_fingerprint": reservation.execution_fingerprint,
        "asset_id": asset_id,
    }
    vectors = (
        (
            "panel_id_v1",
            panel_id_object,
            '{"kind":"panel_id_v1","panel_order":1,"source_binding_sha256":"'
            + source_binding_sha256
            + '","version":1}',
            "b7a3a15b6318b54426113079a1d1a8e3518977a8917e4586ab6c6c76d7b6fab7",
        ),
        (
            "raw_prompt_object_v1",
            raw_prompt_object,
            '{"action":"The detective points at the hidden mechanism.",'
            '"background":"A quiet archive room at night, \u591c\u660e\u3051.",'
            '"character_identities":["detective-v1"],'
            '"composition":"Medium shot with the detective on the left.",'
            '"constraints":["No lettering"],"continuity_bindings":["blue-coat"],'
            '"narrative_intent":"The detective discovers the hidden mechanism."}',
            "135f7732ad453b8cc4c5616118c1c71e3168d04c75cabab697867057dfda33d5",
        ),
        (
            "panel_prompt",
            panel_prompt_object,
            '{"action":"The detective points at the hidden mechanism.",'
            '"background":"A quiet archive room at night, \u591c\u660e\u3051.",'
            '"character_identities":["detective-v1"],'
            '"composition":"Medium shot with the detective on the left.",'
            '"constraints":["No lettering"],"continuity_bindings":["blue-coat"],'
            '"narrative_intent":"The detective discovers the hidden mechanism.",'
            '"order":1,"panel_id":"panel-v7-014-'
            'b7a3a15b6318b54426113079a1d1a8e3518977a8917e4586ab6c6c76d7b6fab7",'
            '"rectangle":{"bottom":968750,"left":46875,"right":953125,"top":31250}}',
            "15e0ab56ffd5a958df6f7e8c27186f03370d760cd18efb6f25af434da9cd781e",
        ),
        (
            "panel_provenance_v1",
            provenance_object,
            '{"kind":"panel_provenance_v1","panel_id":"panel-v7-014-'
            'b7a3a15b6318b54426113079a1d1a8e3518977a8917e4586ab6c6c76d7b6fab7",'
            '"panel_order":1,"plan_fingerprint":"'
            'afa1059f29172368f02a165c30cefeeb93ef55520cace07159d80a7e55ebed39",'
            '"plan_id":"plan-v7-014-'
            + source_binding_sha256
            + '","source_binding_sha256":"'
            + source_binding_sha256
            + '","version":1}',
            "a32cee40993f574d79eb63e86242ed5f38a2565488c3edbcbe4cc3bb9ad367c8",
        ),
        (
            "panel_request_v1",
            request_id_object,
            '{"capability_requirements":["text-prompt","png-output"],'
            '"input_reference":"input-v7-014-'
            '135f7732ad453b8cc4c5616118c1c71e3168d04c75cabab697867057dfda33d5",'
            '"input_sha256":"135f7732ad453b8cc4c5616118c1c71e3168d04c75cabab697867057dfda33d5",'
            '"kind":"panel_request_v1","page_id":"page-test",'
            '"panel_id":"panel-v7-014-b7a3a15b6318b54426113079a1d1a8e3518977a8917e4586ab6c6c76d7b6fab7",'
            '"panel_order":1,"panel_prompt":'
            '{"action":"The detective points at the hidden mechanism.",'
            '"background":"A quiet archive room at night, \u591c\u660e\u3051.",'
            '"character_identities":["detective-v1"],'
            '"composition":"Medium shot with the detective on the left.",'
            '"constraints":["No lettering"],"continuity_bindings":["blue-coat"],'
            '"narrative_intent":"The detective discovers the hidden mechanism.",'
            '"order":1,"panel_id":"panel-v7-014-'
            'b7a3a15b6318b54426113079a1d1a8e3518977a8917e4586ab6c6c76d7b6fab7",'
            '"rectangle":{"bottom":968750,"left":46875,"right":953125,"top":31250}},'
            '"plan_fingerprint":"afa1059f29172368f02a165c30cefeeb93ef55520cace07159d80a7e55ebed39",'
            '"plan_id":"plan-v7-014-' + source_binding_sha256 + '","project_id":"project-test",'
            '"provenance_reference":"panel-provenance-v7-014-'
            'a32cee40993f574d79eb63e86242ed5f38a2565488c3edbcbe4cc3bb9ad367c8",'
            '"version":1}',
            "40f7f319442619cd2e1fdaefe1de64d548a386d70fa2b64a58612e6c21c7a53d",
        ),
        (
            "panel_request_fingerprint",
            request_fingerprint_object,
            '{"capability_requirements":["text-prompt","png-output"],'
            '"input_reference":"input-v7-014-'
            '135f7732ad453b8cc4c5616118c1c71e3168d04c75cabab697867057dfda33d5",'
            '"input_sha256":"135f7732ad453b8cc4c5616118c1c71e3168d04c75cabab697867057dfda33d5",'
            '"page_id":"page-test",'
            '"panel_id":"panel-v7-014-b7a3a15b6318b54426113079a1d1a8e3518977a8917e4586ab6c6c76d7b6fab7",'
            '"panel_order":1,"panel_prompt":'
            '{"action":"The detective points at the hidden mechanism.",'
            '"background":"A quiet archive room at night, \u591c\u660e\u3051.",'
            '"character_identities":["detective-v1"],'
            '"composition":"Medium shot with the detective on the left.",'
            '"constraints":["No lettering"],"continuity_bindings":["blue-coat"],'
            '"narrative_intent":"The detective discovers the hidden mechanism.",'
            '"order":1,"panel_id":"panel-v7-014-'
            'b7a3a15b6318b54426113079a1d1a8e3518977a8917e4586ab6c6c76d7b6fab7",'
            '"rectangle":{"bottom":968750,"left":46875,"right":953125,"top":31250}},'
            '"plan_fingerprint":"afa1059f29172368f02a165c30cefeeb93ef55520cace07159d80a7e55ebed39",'
            '"plan_id":"plan-v7-014-' + source_binding_sha256 + '","project_id":"project-test",'
            '"provenance_reference":"panel-provenance-v7-014-'
            'a32cee40993f574d79eb63e86242ed5f38a2565488c3edbcbe4cc3bb9ad367c8",'
            '"request_id":"request-v7-014-'
            '40f7f319442619cd2e1fdaefe1de64d548a386d70fa2b64a58612e6c21c7a53d"}',
            "a24a8f72a8a3930c731a0a395828d7a89b4e97b9e26d44544e4e6c3f97f84785",
        ),
        (
            "panel_attempt_v1",
            attempt_object,
            '{"authorization_reference":"authorization-test",'
            '"kind":"panel_attempt_v1","provider_reference":"provider-comfyui-v7-014",'
            '"request_fingerprint":"a24a8f72a8a3930c731a0a395828d7a89b4e97b9e26d44544e4e6c3f97f84785",'
            '"version":1}',
            "d48f8bd2e440a085072f107374b7fdc4bcddcf16b2a2c3e4d06e27d048830ca3",
        ),
        (
            "provider_configuration_v1",
            configuration_object,
            '{"attempt_id":"attempt-v7-014-'
            'd48f8bd2e440a085072f107374b7fdc4bcddcf16b2a2c3e4d06e27d048830ca3",'
            '"kind":"provider_configuration_v1","model_id":"test-checkpoint.safetensors",'
            '"model_version":"local-checkpoint","output_quality":"medium",'
            '"output_size":"1024x1024","preset_id":null,"preset_version":null,'
            '"profile_id":"profile:v7-04:prompt-only-png","profile_version":"v1",'
            '"provider_id":"comfyui","provider_reference":"provider-comfyui-v7-014",'
            '"requested_seed":"derived-from-attempt","version":1,'
            '"workflow_id":"workflow:v7-04:fixed-core-png","workflow_version":"v1"}',
            provider_configuration_fingerprint,
        ),
        (
            "panel_execution_v1",
            execution_object,
            '{"attempt_id":"attempt-v7-014-'
            'd48f8bd2e440a085072f107374b7fdc4bcddcf16b2a2c3e4d06e27d048830ca3",'
            '"authorization_reference":"authorization-test","kind":"panel_execution_v1",'
            '"provider_configuration_fingerprint":"'
            + provider_configuration_fingerprint
            + '","provider_reference":"provider-comfyui-v7-014",'
            '"request_fingerprint":"a24a8f72a8a3930c731a0a395828d7a89b4e97b9e26d44544e4e6c3f97f84785",'
            '"version":1}',
            "541398ee54df33638588ab3c63eaba6f48c6a37d3fe67c25dbf36f36187c07e1",
        ),
        (
            "panel_asset_id_v1",
            asset_id_object,
            '{"attempt_id":"attempt-v7-014-'
            'd48f8bd2e440a085072f107374b7fdc4bcddcf16b2a2c3e4d06e27d048830ca3",'
            '"execution_fingerprint":"541398ee54df33638588ab3c63eaba6f48c6a37d3fe67c25dbf36f36187c07e1",'
            '"input_sha256":"135f7732ad453b8cc4c5616118c1c71e3168d04c75cabab697867057dfda33d5",'
            '"kind":"panel_asset_id_v1","media_type":"image/png",'
            '"provenance_reference":"panel-provenance-v7-014-'
            'a32cee40993f574d79eb63e86242ed5f38a2565488c3edbcbe4cc3bb9ad367c8",'
            '"provider_configuration_fingerprint":"'
            + provider_configuration_fingerprint
            + '","request_fingerprint":"a24a8f72a8a3930c731a0a395828d7a89b4e97b9e26d44544e4e6c3f97f84785",'
            '"version":1}',
            "1945138b50b82856e4146ae4883a54b6c0f835f40cb804b8facc22daba49eece",
        ),
        (
            "panel_evidence_id_v1",
            evidence_id_object,
            '{"asset_id":"' + asset_id + '","attempt_id":"attempt-v7-014-'
            'd48f8bd2e440a085072f107374b7fdc4bcddcf16b2a2c3e4d06e27d048830ca3",'
            '"execution_fingerprint":"541398ee54df33638588ab3c63eaba6f48c6a37d3fe67c25dbf36f36187c07e1",'
            '"kind":"panel_evidence_id_v1",'
            '"request_fingerprint":"a24a8f72a8a3930c731a0a395828d7a89b4e97b9e26d44544e4e6c3f97f84785",'
            '"version":1}',
            "a1769421fc16416655c1e339e7988b3b787dda8cefda7f720a22b8192efd446b",
        ),
    )
    for name, value, expected_json, expected_sha256 in vectors:
        actual_json = canonical_json(value)
        assert actual_json == expected_json, name
        assert hashlib.sha256(actual_json.encode("utf-8")).hexdigest() == expected_sha256, name

    assert raw_prompt == canonical_json(raw_prompt_object)
    assert request.input_reference == (
        "input-v7-014-135f7732ad453b8cc4c5616118c1c71e3168d04c75cabab697867057dfda33d5"
    )
    assert (
        request.input_sha256 == "135f7732ad453b8cc4c5616118c1c71e3168d04c75cabab697867057dfda33d5"
    )
    assert request.plan_id == "plan-v7-014-" + source_binding_sha256
    assert request.plan_fingerprint == (
        "afa1059f29172368f02a165c30cefeeb93ef55520cace07159d80a7e55ebed39"
    )
    assert panel.panel_id == (
        "panel-v7-014-b7a3a15b6318b54426113079a1d1a8e3518977a8917e4586ab6c6c76d7b6fab7"
    )
    assert request.provenance_reference == (
        "panel-provenance-v7-014-a32cee40993f574d79eb63e86242ed5f38a2565488c3edbcbe4cc3bb9ad367c8"
    )
    assert request.request_id == (
        "request-v7-014-40f7f319442619cd2e1fdaefe1de64d548a386d70fa2b64a58612e6c21c7a53d"
    )
    assert request.request_fingerprint == (
        "a24a8f72a8a3930c731a0a395828d7a89b4e97b9e26d44544e4e6c3f97f84785"
    )
    assert reservation.attempt_id == (
        "attempt-v7-014-d48f8bd2e440a085072f107374b7fdc4bcddcf16b2a2c3e4d06e27d048830ca3"
    )
    assert reservation.execution_fingerprint == (
        "541398ee54df33638588ab3c63eaba6f48c6a37d3fe67c25dbf36f36187c07e1"
    )
    assert (
        panel_provider_module._configuration_fingerprint(reservation, "test-checkpoint.safetensors")
        == provider_configuration_fingerprint
    )
    assert (
        panel_provider_module._derived_asset_id(request, reservation, "test-checkpoint.safetensors")
        == asset_id
    )
    assert panel_provider_module._derived_evidence_id(reservation, asset_id) == (
        "panel-evidence-v7-014-a1769421fc16416655c1e339e7988b3b787dda8cefda7f720a22b8192efd446b"
    )


def test_preparation_is_read_only_and_prepared_invocation_registers_exact_png(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request, reservation, expected_prompt = _operation_inputs()
    image_bytes = _valid_panel_png()
    events: list[str] = []
    transport = _PreparedTransport(image_bytes, events)
    original_asset_id = panel_provider_module._derived_asset_id
    original_evidence_id = panel_provider_module._derived_evidence_id

    def capture_asset_id(*args: object) -> str:
        events.append("derive_asset_id")
        return original_asset_id(*args)  # type: ignore[arg-type]

    def capture_evidence_id(*args: object) -> str:
        events.append("derive_evidence_id")
        return original_evidence_id(*args)  # type: ignore[arg-type]

    monkeypatch.setattr(panel_provider_module, "_derived_asset_id", capture_asset_id)
    monkeypatch.setattr(panel_provider_module, "_derived_evidence_id", capture_evidence_id)
    provider = LocalFileComfyUIPanelProvider(
        checkpoint_name="test-checkpoint.safetensors",
        owner_root=tmp_path / "assets",
        configuration_report_factory=_configuration_report,
        transport_factory=lambda checkpoint, report: transport,
    )

    prepared = provider.prepare(request, reservation)

    assert callable(prepared)
    assert events == ["derive_asset_id", "derive_evidence_id", "preflight", "prepare"]
    assert transport.request is not None
    assert transport.request.raw_prompt == expected_prompt
    assert not transport.request.raw_prompt.endswith("\n")
    assert transport.request.attempt_id == reservation.attempt_id
    assert transport.request.provider_reference == _PROVIDER_REFERENCE
    execution = prepared()

    assert events == [
        "derive_asset_id",
        "derive_evidence_id",
        "preflight",
        "prepare",
        "submit",
    ]
    assert execution.outcome == "succeeded"
    assert execution.asset is not None
    assert execution.asset.asset_id == (
        "panel-asset-v7-014-1945138b50b82856e4146ae4883a54b6c0f835f40cb804b8facc22daba49eece"
    )
    assert execution.asset.width == 1024
    assert execution.asset.height == 1024
    assert execution.evidence is not None
    assert execution.evidence.evidence_id == (
        "panel-evidence-v7-014-a1769421fc16416655c1e339e7988b3b787dda8cefda7f720a22b8192efd446b"
    )
    assert execution.evidence.provider_reference == _PROVIDER_REFERENCE
    assert execution.image_bytes == image_bytes
    assert provider.read(execution.asset) == image_bytes


def test_existing_v704_transport_submits_only_when_prepared_callable_runs(
    tmp_path: Path,
) -> None:
    request, reservation, expected_prompt = _operation_inputs()
    image_bytes = _valid_panel_png()
    client = _FakeComfyUIHttpClient(image_bytes)
    provider = LocalFileComfyUIPanelProvider(
        checkpoint_name="test-checkpoint.safetensors",
        owner_root=tmp_path / "assets",
        configuration_report_factory=_configuration_report,
        http_client=client,  # type: ignore[arg-type]
        transport_factory=lambda checkpoint, report: ComfyUIImagePrivateTransport(
            checkpoint,
            report,
            http_client=client,  # type: ignore[arg-type]
            poll_limit=2,
            poll_interval_seconds=0,
        ),
    )

    prepared = provider.prepare(request, reservation)

    assert callable(prepared)
    assert "POST /prompt" not in client.calls
    assert "GET /view" not in client.calls
    assert not any(path.startswith("GET /history/") for path in client.calls)
    execution = prepared()

    assert execution.outcome == "succeeded"
    assert execution.asset is not None
    assert execution.image_bytes == image_bytes
    assert client.calls.count("POST /prompt") == 1
    assert client.calls.count("GET /view") == 1
    assert any(path.startswith("GET /history/") for path in client.calls)
    assert hashlib.sha256(expected_prompt.encode("utf-8")).hexdigest() == request.input_sha256
    assert client.submitted is not None
    graph = client.submitted["prompt"]
    assert isinstance(graph, dict)
    assert graph["2"]["inputs"]["text"] == expected_prompt


def test_mismatched_configuration_fails_before_preparation_or_submission(
    tmp_path: Path,
) -> None:
    request, reservation, _ = _operation_inputs()
    events: list[str] = []
    transport = _PreparedTransport(_valid_panel_png(), events)
    provider = LocalFileComfyUIPanelProvider(
        checkpoint_name="test-checkpoint.safetensors",
        owner_root=tmp_path / "assets",
        configuration_report_factory=lambda req, res, checkpoint: _configuration_report(
            req, res, "different-checkpoint.safetensors"
        ),
        transport_factory=lambda checkpoint, report: transport,
    )

    assert provider.prepare(request, reservation) is None
    assert events == []


def test_non_1024_png_is_rejected_after_submit_without_success_evidence(
    tmp_path: Path,
) -> None:
    request, reservation, _ = _operation_inputs()
    events: list[str] = []
    provider = LocalFileComfyUIPanelProvider(
        checkpoint_name="test-checkpoint.safetensors",
        owner_root=tmp_path / "assets",
        configuration_report_factory=_configuration_report,
        transport_factory=lambda checkpoint, report: _PreparedTransport(
            encode_rgb_png(1, 1, b"\x00\x00\x00"), events
        ),
    )

    prepared = provider.prepare(request, reservation)

    assert callable(prepared)
    execution = prepared()
    assert execution.outcome == "recovery_required"
    assert execution.asset is None
    assert execution.evidence is None


def test_untyped_transport_result_is_rejected_without_success_evidence(
    tmp_path: Path,
) -> None:
    request, reservation, _ = _operation_inputs()
    events: list[str] = []
    transport = _PreparedTransport(
        _valid_panel_png(),
        events,
        SimpleNamespace(
            outcome="succeeded",
            output_material=ComfyUIInMemoryGeneratedImageMaterial(_valid_panel_png()),
        ),
    )
    provider = LocalFileComfyUIPanelProvider(
        checkpoint_name="test-checkpoint.safetensors",
        owner_root=tmp_path / "assets",
        configuration_report_factory=_configuration_report,
        transport_factory=lambda checkpoint, report: transport,
    )

    prepared = provider.prepare(request, reservation)

    assert callable(prepared)
    execution = prepared()
    assert execution.outcome == "recovery_required"
    assert execution.asset is None
    assert execution.evidence is None
    assert provider.invoke(request, reservation).outcome == "recovery_required"
    assert events == ["preflight", "prepare", "submit"]


def test_raw_prompt_input_hash_mismatch_blocks_before_transport_creation(
    tmp_path: Path,
) -> None:
    request, reservation, _ = _operation_inputs()
    request = request.model_copy(update={"input_sha256": "0" * 64})
    events: list[str] = []
    provider = LocalFileComfyUIPanelProvider(
        checkpoint_name="test-checkpoint.safetensors",
        owner_root=tmp_path / "assets",
        configuration_report_factory=_configuration_report,
        transport_factory=lambda checkpoint, report: _PreparedTransport(
            encode_rgb_png(1, 1, b"\x00\x00\x00"), events
        ),
    )

    assert provider.prepare(request, reservation) is None
    assert events == []


@pytest.mark.parametrize("wrong_result", [False, True])
def test_exact_owner_binding_is_required_at_capture_and_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, wrong_result: bool
) -> None:
    from dataclasses import replace

    from manga_director.production.next_generation_local_durable_asset_owner import (
        LocalDurableAssetOwner,
    )

    request, reservation, _ = _operation_inputs()
    events: list[str] = []
    provider = LocalFileComfyUIPanelProvider(
        checkpoint_name="test-checkpoint.safetensors",
        owner_root=tmp_path / "assets",
        configuration_report_factory=_configuration_report,
        transport_factory=lambda _checkpoint, _report: _PreparedTransport(
            _valid_panel_png(), events
        ),
    )
    if wrong_result:
        real_register = LocalDurableAssetOwner._register_v714_panel_asset

        def wrong_id(owner, material, asset_id):
            result = real_register(owner, material, asset_id)
            assert result.output is not None
            return replace(
                result, output=result.output.model_copy(update={"output_asset_id": "wrong-id"})
            )

        monkeypatch.setattr(LocalDurableAssetOwner, "_register_v714_panel_asset", wrong_id)
    prepared = provider.prepare(request, reservation)
    assert prepared is not None
    execution = prepared()
    assert events.count("submit") == 1
    if wrong_result:
        assert execution.outcome == "recovery_required"
        assert execution.asset is None and execution.evidence is None
    else:
        assert execution.outcome == "succeeded"
        assert execution.asset is not None and execution.evidence is not None
        inventory = LocalDurableAssetOwner.observe_attempts(
            tmp_path / "assets", (reservation.attempt_id,)
        )
        assert inventory.outcome == "found"
        assert inventory.bindings[0].output_asset_id == execution.asset.asset_id
        assert execution.evidence.output_asset_id == execution.asset.asset_id
        assert provider.read(execution.asset.model_copy(update={"asset_id": "wrong-id"})) is None


def test_read_fails_closed_without_owner_binding(tmp_path: Path) -> None:
    import sqlite3

    request, reservation, _ = _operation_inputs()
    provider = LocalFileComfyUIPanelProvider(
        checkpoint_name="test-checkpoint.safetensors",
        owner_root=tmp_path / "assets",
        configuration_report_factory=_configuration_report,
        transport_factory=lambda _checkpoint, _report: _PreparedTransport(_valid_panel_png(), []),
    )
    prepared = provider.prepare(request, reservation)
    assert prepared is not None
    execution = prepared()
    assert execution.asset is not None
    with sqlite3.connect(provider._registration._registry_path) as connection:
        connection.execute("DELETE FROM asset_registry")
    assert provider.read(execution.asset) is None
