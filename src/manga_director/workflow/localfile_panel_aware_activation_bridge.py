"""Private deterministic LocalFile snapshot-to-panel-plan conversion."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Final, Literal, TypedDict, cast

from manga_director.domain.project import Page
from manga_director.domain.state_machine import PageState
from manga_director.production.next_generation_comfyui_fixed_workflow import (
    validate_comfyui_checkpoint_name,
)
from manga_director.production.next_generation_page_generation_mode_claim import (
    PageGenerationModeClaim,
)
from manga_director.production.next_generation_page_generation_plan import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    COMPOSITOR_PROFILE_ID,
    MIN_GUTTER_PX,
    MIN_MARGIN_PX,
    PageGenerationPlan,
    PagePanelSpecification,
    PanelRectangle,
    canonical_digest,
    logical_reference,
    sha256_digest,
)
from manga_director.production.next_generation_panel_execution_attempt import (
    PanelAttemptReservation,
    PanelGenerationRequest,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.local_file_durability import RevisionedProjectSnapshot
from manga_director.workflow.localfile_panel_aware_page_generation import (
    PanelAwarePageGenerationOperation,
    PanelGenerationUnit,
)

_LAYOUT_PROFILE_VERSION: Final[Literal[1]] = 1
_MARGINS = (MIN_MARGIN_PX, MIN_MARGIN_PX, MIN_MARGIN_PX, MIN_MARGIN_PX)
_PROVIDER_REFERENCE = "provider-comfyui-v7-014"
_PROVIDER_ID = "comfyui"
_PROFILE_ID = "profile:v7-04:prompt-only-png"
_PROFILE_VERSION = "v1"
_WORKFLOW_ID = "workflow:v7-04:fixed-core-png"
_WORKFLOW_VERSION = "v1"
_MODEL_VERSION = "local-checkpoint"
_OUTPUT_SIZE = "1024x1024"
_OUTPUT_QUALITY = "medium"


class _SourcePanelV1(TypedDict):
    number: int
    narrative_intent: str
    character_identities: list[str]
    continuity_bindings: list[str]
    action: str
    background: str
    composition: str
    constraints: list[str]
    rectangle: dict[str, int]


@dataclass(frozen=True, slots=True)
class _PageGenerationPlanConversion:
    """Private source-binding evidence retained for later V7-14 slices."""

    plan: PageGenerationPlan
    source_binding_json: str
    source_binding_sha256: str


def _convert_revisioned_page_snapshot(
    repository: LocalFileRepository,
    snapshot: RevisionedProjectSnapshot,
    *,
    page_number: int,
    layout_profile_id: str,
    layout_profile_version: int,
    rectangles: tuple[PanelRectangle, ...],
) -> _PageGenerationPlanConversion:
    """Convert one authoritative PromptBuilt snapshot without inference or repair."""

    authoritative_snapshot = _require_authoritative_snapshot(repository, snapshot)
    project_id, page_id, source_page_number, page_revision, page_fingerprint, page = (
        _snapshot_page_binding(authoritative_snapshot, page_number)
    )
    rectangles = _require_supported_layout(layout_profile_id, layout_profile_version, rectangles)

    storyboard, storyboard_json = _capture_artifact(page.storyboard, "Page.storyboard")
    prompt_built, prompt_built_json = _capture_artifact(page.prompt, "Page.prompt")
    if type(prompt_built.get("prompt_markdown")) is not str:
        raise ValueError("Page.prompt must contain an exact prompt_markdown string")

    storyboard_sha256 = _sha256(storyboard_json.encode("utf-8"))
    prompt_built_sha256 = _sha256(prompt_built_json.encode("utf-8"))
    storyboard_reference = f"storyboard-v7-014-{storyboard_sha256}"
    prompt_built_reference = f"prompt-v7-014-{prompt_built_sha256}"

    source_panels = _source_panels(storyboard, rectangles)

    source_binding_v1: dict[str, object] = {
        "kind": "source_binding_v1",
        "version": 1,
        "project_id": project_id,
        "page_id": page_id,
        "page_number": source_page_number,
        "page_revision": page_revision,
        "page_fingerprint": page_fingerprint,
        "storyboard_reference": storyboard_reference,
        "storyboard_sha256": storyboard_sha256,
        "prompt_built_reference": prompt_built_reference,
        "prompt_built_sha256": prompt_built_sha256,
        "layout": {
            "profile_id": COMPOSITOR_PROFILE_ID,
            "profile_version": _LAYOUT_PROFILE_VERSION,
            "canvas_width": CANVAS_WIDTH,
            "canvas_height": CANVAS_HEIGHT,
            "margins": list(_MARGINS),
            "gutter_px": MIN_GUTTER_PX,
        },
        "panels": source_panels,
    }
    source_binding_json = _canonical_json(source_binding_v1)
    source_binding_sha256 = _sha256(source_binding_json.encode("utf-8"))
    plan_id = f"plan-v7-014-{source_binding_sha256}"

    panel_specs: list[PagePanelSpecification] = []
    for source_panel, rectangle in zip(source_panels, rectangles, strict=True):
        order = source_panel["number"]
        panel_id_preimage = {
            "kind": "panel_id_v1",
            "version": 1,
            "source_binding_sha256": source_binding_sha256,
            "panel_order": order,
        }
        panel_id = f"panel-v7-014-{_sha256(_canonical_json(panel_id_preimage).encode('utf-8'))}"
        panel_specs.append(
            PagePanelSpecification(
                panel_id=panel_id,
                order=order,
                rectangle=rectangle,
                narrative_intent=source_panel["narrative_intent"],
                character_identities=tuple(source_panel["character_identities"]),
                continuity_bindings=tuple(source_panel["continuity_bindings"]),
                action=source_panel["action"],
                background=source_panel["background"],
                composition=source_panel["composition"],
                constraints=tuple(source_panel["constraints"]),
            )
        )

    plan = PageGenerationPlan(
        plan_id=plan_id,
        project_id=project_id,
        page_id=page_id,
        page_number=source_page_number,
        storyboard_reference=storyboard_reference,
        storyboard_sha256=storyboard_sha256,
        prompt_built_reference=prompt_built_reference,
        prompt_built_sha256=prompt_built_sha256,
        layout_profile_id=COMPOSITOR_PROFILE_ID,
        layout_profile_version=_LAYOUT_PROFILE_VERSION,
        canvas_width=CANVAS_WIDTH,
        canvas_height=CANVAS_HEIGHT,
        margins=_MARGINS,
        gutter_px=MIN_GUTTER_PX,
        panel_count=len(panel_specs),
        panels=tuple(panel_specs),
    )
    return _PageGenerationPlanConversion(
        plan=plan,
        source_binding_json=source_binding_json,
        source_binding_sha256=source_binding_sha256,
    )


def _build_panel_aware_page_generation_operation(
    repository: LocalFileRepository,
    snapshot: RevisionedProjectSnapshot,
    *,
    page_number: int,
    layout_profile_id: str,
    layout_profile_version: int,
    rectangles: tuple[PanelRectangle, ...],
    mode_claim: PageGenerationModeClaim,
    authorization_references: tuple[str, ...],
    composition_authorization_reference: str,
    checkpoint_name: str,
) -> PanelAwarePageGenerationOperation:
    """Compose exact private request, reservation, and composition bindings."""

    conversion = _convert_revisioned_page_snapshot(
        repository,
        snapshot,
        page_number=page_number,
        layout_profile_id=layout_profile_id,
        layout_profile_version=layout_profile_version,
        rectangles=rectangles,
    )
    source_binding = json.loads(conversion.source_binding_json)
    if type(source_binding) is not dict:
        raise ValueError("canonical source binding must be an object")
    page_revision = logical_reference(source_binding.get("page_revision"), "page_revision")
    page_fingerprint_value = source_binding.get("page_fingerprint")
    if type(page_fingerprint_value) is not str:
        raise ValueError("canonical source binding page fingerprint must be a string")
    page_fingerprint = sha256_digest(page_fingerprint_value)
    _require_mode_claim_matches(
        mode_claim,
        plan=conversion.plan,
        page_revision=page_revision,
        page_fingerprint=page_fingerprint,
    )
    if (
        type(authorization_references) is not tuple
        or len(authorization_references) != conversion.plan.panel_count
    ):
        raise ValueError("one issued authorization reference is required per panel")
    panel_authorizations = tuple(
        logical_reference(value, "panel authorization reference")
        for value in authorization_references
    )
    composition_authorization_reference = logical_reference(
        composition_authorization_reference, "composition authorization reference"
    )
    checkpoint_name = validate_comfyui_checkpoint_name(checkpoint_name)

    requests: list[PanelGenerationRequest] = []
    reservations: list[PanelAttemptReservation] = []
    for panel, authorization_reference in zip(
        conversion.plan.panels, panel_authorizations, strict=True
    ):
        raw_prompt_object = {
            "action": panel.action,
            "background": panel.background,
            "character_identities": list(panel.character_identities),
            "composition": panel.composition,
            "constraints": list(panel.constraints),
            "continuity_bindings": list(panel.continuity_bindings),
            "narrative_intent": panel.narrative_intent,
        }
        raw_prompt = _canonical_json(raw_prompt_object)
        input_sha256 = _sha256(raw_prompt.encode("utf-8"))
        input_reference = f"input-v7-014-{input_sha256}"
        panel_prompt = panel.model_dump(mode="json")
        provenance_reference = _prefixed_digest(
            "panel-provenance-v7-014-",
            {
                "kind": "panel_provenance_v1",
                "version": 1,
                "source_binding_sha256": conversion.source_binding_sha256,
                "plan_id": conversion.plan.plan_id,
                "plan_fingerprint": conversion.plan.plan_fingerprint,
                "panel_id": panel.panel_id,
                "panel_order": panel.order,
            },
        )
        request_id = _prefixed_digest(
            "request-v7-014-",
            {
                "kind": "panel_request_v1",
                "version": 1,
                "plan_id": conversion.plan.plan_id,
                "plan_fingerprint": conversion.plan.plan_fingerprint,
                "project_id": conversion.plan.project_id,
                "page_id": conversion.plan.page_id,
                "panel_id": panel.panel_id,
                "panel_order": panel.order,
                "panel_prompt": panel_prompt,
                "capability_requirements": ["text-prompt", "png-output"],
                "input_reference": input_reference,
                "input_sha256": input_sha256,
                "provenance_reference": provenance_reference,
            },
        )
        request = PanelGenerationRequest(
            request_id=request_id,
            plan_id=conversion.plan.plan_id,
            plan_fingerprint=conversion.plan.plan_fingerprint or "",
            project_id=conversion.plan.project_id,
            page_id=conversion.plan.page_id,
            panel_id=panel.panel_id,
            panel_order=panel.order,
            panel_prompt=panel,
            capability_requirements=("text-prompt", "png-output"),
            input_reference=input_reference,
            input_sha256=input_sha256,
            provenance_reference=provenance_reference,
        )
        attempt_id = _prefixed_digest(
            "attempt-v7-014-",
            {
                "kind": "panel_attempt_v1",
                "version": 1,
                "request_fingerprint": request.request_fingerprint,
                "provider_reference": _PROVIDER_REFERENCE,
                "authorization_reference": authorization_reference,
            },
        )
        provider_configuration_fingerprint = canonical_digest(
            {
                "kind": "provider_configuration_v1",
                "version": 1,
                "attempt_id": attempt_id,
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
        execution_fingerprint = canonical_digest(
            {
                "kind": "panel_execution_v1",
                "version": 1,
                "attempt_id": attempt_id,
                "request_fingerprint": request.request_fingerprint,
                "provider_reference": _PROVIDER_REFERENCE,
                "authorization_reference": authorization_reference,
                "provider_configuration_fingerprint": provider_configuration_fingerprint,
            }
        )
        reservation = PanelAttemptReservation(
            attempt_id=attempt_id,
            plan_id=request.plan_id,
            plan_fingerprint=request.plan_fingerprint,
            project_id=request.project_id,
            page_id=request.page_id,
            panel_id=request.panel_id,
            panel_order=request.panel_order,
            request_id=request.request_id,
            request_fingerprint=request.request_fingerprint or "",
            provider_reference=_PROVIDER_REFERENCE,
            authorization_reference=authorization_reference,
            execution_fingerprint=execution_fingerprint,
        )
        requests.append(request)
        reservations.append(reservation)

    ordered_request_fingerprints = [request.request_fingerprint for request in requests]
    ordered_attempt_ids = [reservation.attempt_id for reservation in reservations]
    composition_provenance_reference = _prefixed_digest(
        "composition-provenance-v7-014-",
        {
            "kind": "composition_provenance_v1",
            "version": 1,
            "source_binding_sha256": conversion.source_binding_sha256,
            "plan_id": conversion.plan.plan_id,
            "plan_fingerprint": conversion.plan.plan_fingerprint,
            "ordered_request_fingerprints": ordered_request_fingerprints,
            "ordered_attempt_ids": ordered_attempt_ids,
        },
    )
    composition_attempt_id = _prefixed_digest(
        "composition-attempt-v7-014-",
        {
            "kind": "composition_attempt_v1",
            "version": 1,
            "plan_id": conversion.plan.plan_id,
            "plan_fingerprint": conversion.plan.plan_fingerprint,
            "page_revision": page_revision,
            "composition_authorization_reference": composition_authorization_reference,
            "composition_provenance_reference": composition_provenance_reference,
            "compositor_profile_id": COMPOSITOR_PROFILE_ID,
            "compositor_profile_version": _LAYOUT_PROFILE_VERSION,
            "ordered_request_fingerprints": ordered_request_fingerprints,
            "ordered_attempt_ids": ordered_attempt_ids,
        },
    )
    composition_evidence_id = _prefixed_digest(
        "composition-evidence-v7-014-",
        {
            "kind": "composition_evidence_id_v1",
            "version": 1,
            "composition_attempt_id": composition_attempt_id,
            "plan_id": conversion.plan.plan_id,
            "plan_fingerprint": conversion.plan.plan_fingerprint,
        },
    )
    composite_asset_id = _prefixed_digest(
        "composite-asset-v7-014-",
        {
            "kind": "composite_asset_id_v1",
            "version": 1,
            "composition_attempt_id": composition_attempt_id,
            "plan_id": conversion.plan.plan_id,
            "plan_fingerprint": conversion.plan.plan_fingerprint,
            "media_type": "image/png",
        },
    )
    application_id = _prefixed_digest(
        "composition-application-v7-014-",
        {
            "kind": "composition_application_id_v1",
            "version": 1,
            "composition_attempt_id": composition_attempt_id,
            "plan_id": conversion.plan.plan_id,
            "plan_fingerprint": conversion.plan.plan_fingerprint,
            "project_id": conversion.plan.project_id,
            "page_id": conversion.plan.page_id,
            "page_revision": page_revision,
        },
    )
    return PanelAwarePageGenerationOperation(
        plan=conversion.plan,
        mode_claim=mode_claim,
        panel_units=tuple(
            PanelGenerationUnit(request, reservation)
            for request, reservation in zip(requests, reservations, strict=True)
        ),
        page_revision=page_revision,
        composition_attempt_id=composition_attempt_id,
        composition_authorization_reference=composition_authorization_reference,
        composition_provenance_reference=composition_provenance_reference,
        composition_evidence_id=composition_evidence_id,
        composite_asset_id=composite_asset_id,
        application_id=application_id,
    )


def _require_mode_claim_matches(
    claim: PageGenerationModeClaim,
    *,
    plan: PageGenerationPlan,
    page_revision: str,
    page_fingerprint: str,
) -> None:
    if type(claim) is not PageGenerationModeClaim or (
        claim.mode != "panel_aware"
        or claim.project_id != plan.project_id
        or claim.page_id != plan.page_id
        or claim.page_revision != page_revision
        or claim.page_fingerprint != page_fingerprint
        or claim.source_state != "PromptBuilt"
        or claim.mode_binding_reference != plan.plan_id
        or claim.status != "active"
    ):
        raise ValueError("mode claim must bind the exact Page snapshot and plan")


def _require_authoritative_snapshot(
    repository: LocalFileRepository, snapshot: RevisionedProjectSnapshot
) -> RevisionedProjectSnapshot:
    if type(repository) is not LocalFileRepository:
        raise ValueError("the authoritative LocalFile repository is required")
    if type(snapshot) is not RevisionedProjectSnapshot:
        raise ValueError("an authoritative revisioned Page snapshot is required")
    authoritative = repository._load_revisioned(snapshot.project.id)
    if (
        authoritative.revision != snapshot.revision
        or authoritative.fingerprint != snapshot.fingerprint
        or authoritative.project != snapshot.project
    ):
        raise ValueError("revisioned Page snapshot does not match LocalFile authority")
    return authoritative


def _snapshot_page_binding(
    snapshot: RevisionedProjectSnapshot, page_number: int
) -> tuple[str, str, int, str, str, Page]:
    if type(page_number) is not int or page_number <= 0:
        raise ValueError("page_number must be a positive integer")
    if type(snapshot.revision) is not int or snapshot.revision <= 0:
        raise ValueError("snapshot revision must be a positive integer")
    page_fingerprint = sha256_digest(snapshot.fingerprint)
    project_id = logical_reference(snapshot.project.id, "project_id")
    page_revision = logical_reference(f"revision-{snapshot.revision}", "page_revision")

    page = snapshot.project.page(page_number)
    if (
        type(page.page_number) is not int
        or page.page_number <= 0
        or page.page_number != page_number
        or page.state is not PageState.PROMPT_BUILT
    ):
        raise ValueError("snapshot Page must be the requested PromptBuilt Page")
    source_page_number = page.page_number
    page_id = str(source_page_number)
    return (
        project_id,
        page_id,
        source_page_number,
        page_revision,
        page_fingerprint,
        page,
    )


def _require_supported_layout(
    layout_profile_id: str,
    layout_profile_version: int,
    rectangles: tuple[PanelRectangle, ...],
) -> tuple[PanelRectangle, ...]:
    if layout_profile_id != COMPOSITOR_PROFILE_ID:
        raise ValueError("layout profile is unsupported")
    if type(layout_profile_version) is not int or layout_profile_version != _LAYOUT_PROFILE_VERSION:
        raise ValueError("layout profile version is unsupported")
    if type(rectangles) is not tuple or any(
        type(rectangle) is not PanelRectangle for rectangle in rectangles
    ):
        raise ValueError("layout rectangles must be an ordered PanelRectangle tuple")
    return tuple(
        PanelRectangle(
            left=rectangle.left,
            top=rectangle.top,
            right=rectangle.right,
            bottom=rectangle.bottom,
        )
        for rectangle in rectangles
    )


def _source_panels(
    storyboard: dict[str, object], rectangles: tuple[PanelRectangle, ...]
) -> list[_SourcePanelV1]:
    panels = storyboard.get("panels")
    if type(panels) is not list or not panels:
        raise ValueError("Page.storyboard panels must be a non-empty ordered list")
    ordered_panels = cast(list[object], panels)
    if len(rectangles) != len(ordered_panels):
        raise ValueError("layout must provide exactly one rectangle per panel")

    source_panels: list[_SourcePanelV1] = []
    for expected_number, (panel, rectangle) in enumerate(
        zip(ordered_panels, rectangles, strict=True), start=1
    ):
        if type(panel) is not dict:
            raise ValueError("each persisted Storyboard panel must be an object")
        panel_values = cast(dict[str, object], panel)
        number = panel_values.get("number")
        if type(number) is not int or number != expected_number:
            raise ValueError("panel numbers must be strict integers in persisted 1..N order")
        source_panels.append(
            {
                "number": number,
                "narrative_intent": _required_string(panel_values, "narrative_intent"),
                "character_identities": _required_string_list(panel_values, "characters"),
                "continuity_bindings": _required_string_list(panel_values, "continuity_bindings"),
                "action": _required_string(panel_values, "action"),
                "background": _required_string(panel_values, "background"),
                "composition": _required_string(panel_values, "composition"),
                "constraints": _required_string_list(panel_values, "constraints"),
                "rectangle": {
                    "left": rectangle.left,
                    "top": rectangle.top,
                    "right": rectangle.right,
                    "bottom": rectangle.bottom,
                },
            }
        )
    return source_panels


def _capture_artifact(value: object, label: str) -> tuple[dict[str, object], str]:
    if type(value) is not dict:
        raise ValueError(f"{label} must be a persisted dictionary")
    try:
        canonical = _canonical_json(value)
        captured = json.loads(canonical)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain canonical JSON values") from exc
    if type(captured) is not dict:
        raise ValueError(f"{label} must be a persisted dictionary")
    return cast(dict[str, object], captured), canonical


def _required_value(panel: dict[str, object], key: str) -> object:
    if key not in panel:
        raise ValueError(f"Storyboard panel requires explicit {key}")
    return panel[key]


def _required_string(panel: dict[str, object], key: str) -> str:
    value = _required_value(panel, key)
    if type(value) is not str:
        raise ValueError(f"Storyboard panel requires explicit string {key}")
    return value


def _required_string_list(panel: dict[str, object], key: str) -> list[str]:
    value = _required_value(panel, key)
    if type(value) is not list or not value or any(type(item) is not str for item in value):
        raise ValueError(f"Storyboard panel {key} must be a non-empty ordered string list")
    return cast(list[str], value)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _prefixed_digest(prefix: str, value: object) -> str:
    return f"{prefix}{_sha256(_canonical_json(value).encode('utf-8'))}"
