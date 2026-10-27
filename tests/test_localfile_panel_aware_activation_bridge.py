from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production.next_generation_page_generation_mode_claim import (
    PageGenerationModeClaim,
)
from manga_director.production.next_generation_page_generation_plan import PanelRectangle
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.local_file_durability import RevisionedProjectSnapshot
from manga_director.workflow.localfile_panel_aware_activation_bridge import (
    _build_panel_aware_page_generation_operation,
    _convert_revisioned_page_snapshot,
    _snapshot_page_binding,
)


def _rectangle(left: int = 50_000, right: int = 950_000) -> PanelRectangle:
    return PanelRectangle(left=left, top=40_000, right=right, bottom=960_000)


def _panel(**changes: object) -> dict[str, object]:
    panel: dict[str, object] = {
        "number": 1,
        "role": "setup",
        "camera": "medium shot",
        "expression": "focused",
        "dialogue": ["Do not infer from this."],
        "sound_effect": "tap",
        "balloon_position": "upper right",
        "narrative_intent": "Aki discovers the sealed archive door.",
        "characters": ["character-aki-v1"],
        "continuity_bindings": ["costume-aki-blue-coat-v2"],
        "action": "Aki places the brass key into the archive lock.",
        "background": "The east archive corridor before sunrise.",
        "composition": "Medium shot with Aki left and the lock in the foreground.",
        "constraints": ["Keep the blue coat and brass key visible."],
    }
    panel.update(changes)
    return panel


def _snapshot(
    tmp_path: Path,
    *,
    storyboard: dict[str, object] | None = None,
    prompt: dict[str, object] | None = None,
    page_number: int = 1,
    root_name: str = "repository",
) -> tuple[LocalFileRepository, RevisionedProjectSnapshot]:
    page = Page(
        page_number=page_number,
        state=PageState.PROMPT_BUILT,
        page_design={},
        review={},
        storyboard=(
            storyboard if storyboard is not None else {"panels": [_panel()], "title": "夜明け"}
        ),
        dialogue={},
        prompt=(
            prompt if prompt is not None else {"prompt_markdown": "夜明けの鍵 🔑", "tokens": 12}
        ),
    )
    project = Project(
        id="project-v7-014",
        title="V7-14",
        pages=[page],
        created_at=datetime(2026, 10, 27, tzinfo=UTC),
        updated_at=datetime(2026, 10, 27, tzinfo=UTC),
    )
    repository = LocalFileRepository((tmp_path / root_name).resolve())
    repository.save(project)
    return repository, repository._load_revisioned(project.id)


def _convert(
    tmp_path: Path,
    source: tuple[LocalFileRepository, RevisionedProjectSnapshot] | None = None,
    *,
    page_number: int = 1,
    layout_profile_id: str = "md-page-compositor-v1",
    layout_profile_version: int = 1,
    rectangles: tuple[PanelRectangle, ...] = (_rectangle(),),
):
    repository, snapshot = source or _snapshot(tmp_path)
    return _convert_revisioned_page_snapshot(
        repository,
        snapshot,
        page_number=page_number,
        layout_profile_id=layout_profile_id,
        layout_profile_version=layout_profile_version,
        rectangles=rectangles,
    )


def _mode_claim(
    source: tuple[LocalFileRepository, RevisionedProjectSnapshot], plan_id: str
) -> PageGenerationModeClaim:
    repository, snapshot = source
    project_id, page_id, _number, page_revision, page_fingerprint, _page = _snapshot_page_binding(
        snapshot, 1
    )
    return PageGenerationModeClaim(
        claim_id="claim-v7-014-test",
        project_id=project_id,
        page_id=page_id,
        page_revision=page_revision,
        page_fingerprint=page_fingerprint,
        mode="panel_aware",
        mode_binding_reference=plan_id,
        authorizer_reference="mode-authorizer-v7-014-test",
    )


def _build_operation(
    tmp_path: Path,
    source: tuple[LocalFileRepository, RevisionedProjectSnapshot] | None = None,
    *,
    mode_claim: PageGenerationModeClaim | None = None,
    authorization_references: tuple[str, ...] = ("authorization-v7-014-panel-1",),
):
    resolved_source = source or _snapshot(tmp_path)
    conversion = _convert(tmp_path, resolved_source)
    claim = mode_claim or _mode_claim(resolved_source, conversion.plan.plan_id)
    return _build_panel_aware_page_generation_operation(
        *resolved_source,
        page_number=1,
        layout_profile_id="md-page-compositor-v1",
        layout_profile_version=1,
        rectangles=(_rectangle(),),
        mode_claim=claim,
        authorization_references=authorization_references,
        composition_authorization_reference="composition-authorization-v7-014-test",
        checkpoint_name="checkpoint_test.safetensors",
    )


def test_operation_composition_is_deterministic_and_exactly_bound(
    tmp_path: Path,
) -> None:
    source = _snapshot(tmp_path)
    first = _build_operation(tmp_path, source)
    second = _build_operation(tmp_path, source)

    assert first == second
    assert first.page_revision == first.mode_claim.page_revision
    assert first.mode_claim.page_fingerprint == _snapshot_page_binding(source[1], 1)[4]
    assert first.mode_claim.mode == "panel_aware"
    assert first.mode_claim.mode_binding_reference == first.plan.plan_id
    assert len(first.panel_units) == first.plan.panel_count == 1
    request = first.panel_units[0].request
    reservation = first.panel_units[0].reservation
    assert request.panel_prompt == first.plan.panels[0]
    assert request.request_fingerprint == reservation.request_fingerprint
    assert request.request_id == reservation.request_id
    raw_prompt_object = {
        "action": "Aki places the brass key into the archive lock.",
        "background": "The east archive corridor before sunrise.",
        "character_identities": ["character-aki-v1"],
        "composition": "Medium shot with Aki left and the lock in the foreground.",
        "constraints": ["Keep the blue coat and brass key visible."],
        "continuity_bindings": ["costume-aki-blue-coat-v2"],
        "narrative_intent": "Aki discovers the sealed archive door.",
    }
    raw_prompt = json.dumps(
        raw_prompt_object, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    assert raw_prompt == (
        '{"action":"Aki places the brass key into the archive lock.",'
        '"background":"The east archive corridor before sunrise.",'
        '"character_identities":["character-aki-v1"],'
        '"composition":"Medium shot with Aki left and the lock in the foreground.",'
        '"constraints":["Keep the blue coat and brass key visible."],'
        '"continuity_bindings":["costume-aki-blue-coat-v2"],'
        '"narrative_intent":"Aki discovers the sealed archive door."}'
    )
    assert hashlib.sha256(raw_prompt.encode("utf-8")).hexdigest() == (
        "32d40e478262ff87ee3fa44b47883f76a8f963b260bd668d85fa03618ff91629"
    )
    assert request.input_sha256 == (
        "32d40e478262ff87ee3fa44b47883f76a8f963b260bd668d85fa03618ff91629"
    )
    assert request.input_reference == (
        "input-v7-014-32d40e478262ff87ee3fa44b47883f76a8f963b260bd668d85fa03618ff91629"
    )
    assert request.request_id == (
        "request-v7-014-8c9b73caeeb2af3e6321f965cea175e568197aaa6384da96eb1080b6fa257a2f"
    )
    assert request.request_fingerprint == (
        "0be3469e90ba95d2ea2cea90c940d802f2b8cd2ae5a4af62869c28de5411ec3c"
    )
    assert request.provenance_reference == (
        "panel-provenance-v7-014-cd6dfa540c522a9c4c89ee8de6f951381fdf473fa7b4ad6142630700c7e3f719"
    )
    assert reservation.attempt_id == (
        "attempt-v7-014-ab955689dd7e096140be73d461489e97df3e642ff17b4ec5ef66972033a25466"
    )
    assert reservation.provider_reference == "provider-comfyui-v7-014"
    assert reservation.authorization_reference == "authorization-v7-014-panel-1"
    assert reservation.execution_fingerprint == (
        "f2616813a83b972e6165da50b0d43b4842c455a3095e50fc38d9f0c312171516"
    )
    assert first.composition_provenance_reference == (
        "composition-provenance-v7-014-0933af381a12615b78d05863bf2fb6c57b98d22f9f0f79ddd3b26129be11a0ed"
    )
    assert first.composition_attempt_id == (
        "composition-attempt-v7-014-bed237de1e4b7200766105b87bbd9ef969d5fe811bffb91cb6742d3f1f9b64b7"
    )
    assert first.composition_evidence_id == (
        "composition-evidence-v7-014-8cbf891802143d8a2d244af022b542605adfec19fad063dcda432fba0714ac03"
    )
    assert first.composite_asset_id == (
        "composite-asset-v7-014-2cf7e0d57f070e5fed48fb1022e4fdb639ebd019dfb94530414c2998d89d89cc"
    )
    assert first.application_id == (
        "composition-application-v7-014-5544b719a856ac8b9cc7ab65eb1a5bc5fa5451cf6baf3472951b22f5b6ed3df8"
    )


def test_two_panel_operation_pins_ordered_composition_golden_bindings(
    tmp_path: Path,
) -> None:
    rectangles = (
        _rectangle(50_000, 450_000),
        PanelRectangle(left=500_000, top=40_000, right=950_000, bottom=960_000),
    )
    source = _snapshot(
        tmp_path,
        storyboard={"panels": [_panel(number=1), _panel(number=2)], "title": "夜明け"},
    )
    conversion = _convert(tmp_path, source, rectangles=rectangles)
    operation = _build_panel_aware_page_generation_operation(
        *source,
        page_number=1,
        layout_profile_id="md-page-compositor-v1",
        layout_profile_version=1,
        rectangles=rectangles,
        mode_claim=_mode_claim(source, conversion.plan.plan_id),
        authorization_references=(
            "authorization-v7-014-panel-1",
            "authorization-v7-014-panel-2",
        ),
        composition_authorization_reference="composition-authorization-v7-014-test",
        checkpoint_name="checkpoint_test.safetensors",
    )
    units = operation.panel_units
    assert tuple(unit.request.panel_order for unit in units) == (1, 2)
    assert tuple(unit.request.panel_id for unit in units) == tuple(
        panel.panel_id for panel in operation.plan.panels
    )
    assert tuple(unit.request.request_fingerprint for unit in units) == (
        "8437485c6960fbd89277dcdf7319df41fb2602f592a0af3660aa5e314932a4a3",
        "32f173c6c5563ab7ea9e176f5bf46cc36e060d16217ff068926d734dd125ea95",
    )
    assert tuple(unit.reservation.attempt_id for unit in units) == (
        "attempt-v7-014-2f841cac874830381d3255aa445d94837076f5984aab040a5ad1ff96a602f809",
        "attempt-v7-014-14383269ba4b618c2f258e67ca384024fdb5ade934887e8b0a7f93cd6b8c4819",
    )

    composition_provenance_preimage = (
        '{"kind":"composition_provenance_v1","ordered_attempt_ids":['
        '"attempt-v7-014-2f841cac874830381d3255aa445d94837076f5984aab040a5ad1ff96a602f809",'
        '"attempt-v7-014-14383269ba4b618c2f258e67ca384024fdb5ade934887e8b0a7f93cd6b8c4819"],'
        '"ordered_request_fingerprints":['
        '"8437485c6960fbd89277dcdf7319df41fb2602f592a0af3660aa5e314932a4a3",'
        '"32f173c6c5563ab7ea9e176f5bf46cc36e060d16217ff068926d734dd125ea95"],'
        '"plan_fingerprint":"055e3240ea86535bfbf2f16cbf7c413e8a550afc22396274b1f325cd9c32087f",'
        '"plan_id":"plan-v7-014-1d9a2a5fca619b0f9990d4bf59ec57b725af36b12c25340b3284388bf47e8d43",'
        '"source_binding_sha256":"1d9a2a5fca619b0f9990d4bf59ec57b725af36b12c25340b3284388bf47e8d43",'
        '"version":1}'
    )
    assert hashlib.sha256(composition_provenance_preimage.encode("utf-8")).hexdigest() == (
        "c3c76c65ebef9fd9aa6076901e9d352f97e8a2e4a8dae2f94b1721a06e0e80e8"
    )
    assert operation.composition_provenance_reference == (
        "composition-provenance-v7-014-c3c76c65ebef9fd9aa6076901e9d352f97e8a2e4a8dae2f94b1721a06e0e80e8"
    )

    composition_attempt_preimage = (
        '{"composition_authorization_reference":"composition-authorization-v7-014-test",'
        '"composition_provenance_reference":"composition-provenance-v7-014-c3c76c65ebef9fd9aa6076901e9d352f97e8a2e4a8dae2f94b1721a06e0e80e8",'
        '"compositor_profile_id":"md-page-compositor-v1","compositor_profile_version":1,'
        '"kind":"composition_attempt_v1","ordered_attempt_ids":['
        '"attempt-v7-014-2f841cac874830381d3255aa445d94837076f5984aab040a5ad1ff96a602f809",'
        '"attempt-v7-014-14383269ba4b618c2f258e67ca384024fdb5ade934887e8b0a7f93cd6b8c4819"],'
        '"ordered_request_fingerprints":['
        '"8437485c6960fbd89277dcdf7319df41fb2602f592a0af3660aa5e314932a4a3",'
        '"32f173c6c5563ab7ea9e176f5bf46cc36e060d16217ff068926d734dd125ea95"],'
        '"page_revision":"revision-1",'
        '"plan_fingerprint":"055e3240ea86535bfbf2f16cbf7c413e8a550afc22396274b1f325cd9c32087f",'
        '"plan_id":"plan-v7-014-1d9a2a5fca619b0f9990d4bf59ec57b725af36b12c25340b3284388bf47e8d43",'
        '"version":1}'
    )
    assert hashlib.sha256(composition_attempt_preimage.encode("utf-8")).hexdigest() == (
        "6afd8c214d5a4f5ad0718eb4996c2de37ebbc121aa71aabde4ac0169af17ffb0"
    )
    assert operation.composition_attempt_id == (
        "composition-attempt-v7-014-6afd8c214d5a4f5ad0718eb4996c2de37ebbc121aa71aabde4ac0169af17ffb0"
    )


def test_operation_composition_rejects_mode_claim_snapshot_mismatch(
    tmp_path: Path,
) -> None:
    source = _snapshot(tmp_path)
    conversion = _convert(tmp_path, source)
    claim = _mode_claim(source, conversion.plan.plan_id).model_copy(
        update={"page_fingerprint": "0" * 64}
    )

    with pytest.raises(ValueError, match="mode claim must bind"):
        _build_operation(tmp_path, source, mode_claim=claim)


def test_operation_composition_requires_one_safe_authorization_per_panel(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="one issued authorization"):
        _build_operation(tmp_path, authorization_references=())

    with pytest.raises(ValueError, match="unsafe|secret|credential|logical"):
        _build_operation(tmp_path, authorization_references=("token-secret-abc",))


def test_valid_snapshot_has_literal_canonical_hashes_and_deterministic_plan(
    tmp_path: Path,
) -> None:
    source = _snapshot(tmp_path)
    first = _convert(tmp_path, source)
    second = _convert(tmp_path, source)
    storyboard_canonical = (
        '{"panels":[{"action":"Aki places the brass key into the archive lock.",'
        '"background":"The east archive corridor before sunrise.",'
        '"balloon_position":"upper right","camera":"medium shot",'
        '"characters":["character-aki-v1"],'
        '"composition":"Medium shot with Aki left and the lock in the foreground.",'
        '"constraints":["Keep the blue coat and brass key visible."],'
        '"continuity_bindings":["costume-aki-blue-coat-v2"],'
        '"dialogue":["Do not infer from this."],"expression":"focused",'
        '"narrative_intent":"Aki discovers the sealed archive door.",'
        '"number":1,"role":"setup","sound_effect":"tap"}],"title":"夜明け"}'
    )
    prompt_canonical = '{"prompt_markdown":"夜明けの鍵 🔑","tokens":12}'
    panel_id_preimage = (
        '{"kind":"panel_id_v1","panel_order":1,'
        '"source_binding_sha256":'
        '"18199a171f6f1a0fd4490fee4a07377fae20a78ab1e555f53bf05b9f188a31d6",'
        '"version":1}'
    )

    assert first == second
    assert first.plan == second.plan
    assert first.plan.plan_fingerprint == (
        "afea4f0c1e658f77d7c706d7600b2331eba0eeeb9562de4c1837c0df204a6d28"
    )
    assert hashlib.sha256(storyboard_canonical.encode("utf-8")).hexdigest() == (
        first.plan.storyboard_sha256
    )
    assert hashlib.sha256(prompt_canonical.encode("utf-8")).hexdigest() == (
        first.plan.prompt_built_sha256
    )
    assert hashlib.sha256(panel_id_preimage.encode("utf-8")).hexdigest() == (
        "cf8315e7255491297614e42bccac38b255e89279f5be3614249195b4b29dedc5"
    )
    assert first.plan.storyboard_sha256 == (
        "5b0f35502281bcb77e9be96d8a0485fd430c811cfc7e44473070ea68a20120a1"
    )
    assert first.plan.prompt_built_sha256 == (
        "26f4eb8261b409e81e99b9de6b016a2cb6bef90d6547b4fdf3c10743527ac23a"
    )
    assert first.source_binding_sha256 == (
        "18199a171f6f1a0fd4490fee4a07377fae20a78ab1e555f53bf05b9f188a31d6"
    )
    assert first.plan.storyboard_reference == (
        "storyboard-v7-014-5b0f35502281bcb77e9be96d8a0485fd430c811cfc7e44473070ea68a20120a1"
    )
    assert first.plan.prompt_built_reference == (
        "prompt-v7-014-26f4eb8261b409e81e99b9de6b016a2cb6bef90d6547b4fdf3c10743527ac23a"
    )
    assert first.plan.plan_id == (
        "plan-v7-014-18199a171f6f1a0fd4490fee4a07377fae20a78ab1e555f53bf05b9f188a31d6"
    )
    assert first.plan.panels[0].panel_id == (
        "panel-v7-014-cf8315e7255491297614e42bccac38b255e89279f5be3614249195b4b29dedc5"
    )
    assert first.source_binding_json == (
        '{"kind":"source_binding_v1","layout":{"canvas_height":3072,'
        '"canvas_width":2048,"gutter_px":48,"margins":[96,96,96,96],'
        '"profile_id":"md-page-compositor-v1","profile_version":1},'
        '"page_fingerprint":"b93735995115014be55305f6f6bbb274b17e52fc8971a3849096c12333eb811b",'
        '"page_id":"1","page_number":1,"page_revision":"revision-1","panels":'
        '[{"action":"Aki places the brass key into the archive lock.",'
        '"background":"The east archive corridor before sunrise.",'
        '"character_identities":["character-aki-v1"],'
        '"composition":"Medium shot with Aki left and the lock in the foreground.",'
        '"constraints":["Keep the blue coat and brass key visible."],'
        '"continuity_bindings":["costume-aki-blue-coat-v2"],'
        '"narrative_intent":"Aki discovers the sealed archive door.","number":1,'
        '"rectangle":{"bottom":960000,"left":50000,"right":950000,"top":40000}}],'
        '"project_id":"project-v7-014","prompt_built_reference":'
        '"prompt-v7-014-26f4eb8261b409e81e99b9de6b016a2cb6bef90d6547b4fdf3c10743527ac23a",'
        '"prompt_built_sha256":"26f4eb8261b409e81e99b9de6b016a2cb6bef90d6547b4fdf3c10743527ac23a",'
        '"storyboard_reference":'
        '"storyboard-v7-014-5b0f35502281bcb77e9be96d8a0485fd430c811cfc7e44473070ea68a20120a1",'
        '"storyboard_sha256":"5b0f35502281bcb77e9be96d8a0485fd430c811cfc7e44473070ea68a20120a1",'
        '"version":1}'
    )
    assert not first.source_binding_json.endswith("\n")


def test_valid_multi_panel_snapshot_has_literal_golden_bindings(tmp_path: Path) -> None:
    panels = [_panel(number=1), _panel(number=2)]
    rectangles = (_rectangle(50_000, 450_000), _rectangle(500_000, 950_000))

    result = _convert(
        tmp_path,
        _snapshot(tmp_path, storyboard={"panels": panels, "title": "夜明け"}),
        rectangles=rectangles,
    )

    assert result.source_binding_json == (
        '{"kind":"source_binding_v1","layout":{"canvas_height":3072,'
        '"canvas_width":2048,"gutter_px":48,"margins":[96,96,96,96],'
        '"profile_id":"md-page-compositor-v1","profile_version":1},'
        '"page_fingerprint":"e77da743a64637a11c2ae0fa26144d9bef7912b331882d76ecc856b36f1a1180",'
        '"page_id":"1","page_number":1,"page_revision":"revision-1","panels":'
        '[{"action":"Aki places the brass key into the archive lock.",'
        '"background":"The east archive corridor before sunrise.",'
        '"character_identities":["character-aki-v1"],'
        '"composition":"Medium shot with Aki left and the lock in the foreground.",'
        '"constraints":["Keep the blue coat and brass key visible."],'
        '"continuity_bindings":["costume-aki-blue-coat-v2"],'
        '"narrative_intent":"Aki discovers the sealed archive door.","number":1,'
        '"rectangle":{"bottom":960000,"left":50000,"right":450000,"top":40000}},'
        '{"action":"Aki places the brass key into the archive lock.",'
        '"background":"The east archive corridor before sunrise.",'
        '"character_identities":["character-aki-v1"],'
        '"composition":"Medium shot with Aki left and the lock in the foreground.",'
        '"constraints":["Keep the blue coat and brass key visible."],'
        '"continuity_bindings":["costume-aki-blue-coat-v2"],'
        '"narrative_intent":"Aki discovers the sealed archive door.","number":2,'
        '"rectangle":{"bottom":960000,"left":500000,"right":950000,"top":40000}}],'
        '"project_id":"project-v7-014","prompt_built_reference":'
        '"prompt-v7-014-26f4eb8261b409e81e99b9de6b016a2cb6bef90d6547b4fdf3c10743527ac23a",'
        '"prompt_built_sha256":"26f4eb8261b409e81e99b9de6b016a2cb6bef90d6547b4fdf3c10743527ac23a",'
        '"storyboard_reference":'
        '"storyboard-v7-014-7350cb5e9a74e99ad819ad7bfd95e383d17282755c0ff93b87b75b56ca08937f",'
        '"storyboard_sha256":"7350cb5e9a74e99ad819ad7bfd95e383d17282755c0ff93b87b75b56ca08937f",'
        '"version":1}'
    )
    assert result.source_binding_sha256 == (
        "1d9a2a5fca619b0f9990d4bf59ec57b725af36b12c25340b3284388bf47e8d43"
    )
    assert result.plan.plan_id == (
        "plan-v7-014-1d9a2a5fca619b0f9990d4bf59ec57b725af36b12c25340b3284388bf47e8d43"
    )
    assert result.plan.plan_fingerprint == (
        "055e3240ea86535bfbf2f16cbf7c413e8a550afc22396274b1f325cd9c32087f"
    )
    assert tuple(panel.panel_id for panel in result.plan.panels) == (
        "panel-v7-014-747c5b4750ec6a3a4ce5e9d42bd95f47cae498029de5fb76643ecbcfff11f509",
        "panel-v7-014-f421dd4cb891b2b8fee1465128f7b30b8f64ac6c017c8d403c08a2768284beb3",
    )


def test_dict_key_order_does_not_change_canonical_hashes(tmp_path: Path) -> None:
    panel = _panel()
    reordered_panel = dict(reversed(tuple(panel.items())))
    storyboard = {"title": "夜明け", "panels": [reordered_panel]}
    prompt = {"tokens": 12, "prompt_markdown": "夜明けの鍵 🔑"}

    result = _convert(
        tmp_path,
        _snapshot(
            tmp_path,
            storyboard=storyboard,
            prompt=prompt,
            root_name="reordered",
        ),
    )
    baseline = _convert(tmp_path, _snapshot(tmp_path, root_name="baseline"))

    assert result.plan.storyboard_sha256 == baseline.plan.storyboard_sha256
    assert result.plan.prompt_built_sha256 == baseline.plan.prompt_built_sha256
    assert result.plan.storyboard_reference == baseline.plan.storyboard_reference
    assert result.plan.prompt_built_reference == baseline.plan.prompt_built_reference


def test_source_artifact_mutation_changes_all_dependent_bindings(tmp_path: Path) -> None:
    original = _convert(tmp_path, _snapshot(tmp_path, root_name="original"))
    changed = _convert(
        tmp_path,
        _snapshot(
            tmp_path,
            storyboard={
                "panels": [_panel(action="Aki turns the brass key in the archive lock.")],
                "title": "夜明け",
            },
            root_name="changed",
        ),
    )

    assert changed.plan.storyboard_sha256 != original.plan.storyboard_sha256
    assert changed.plan.storyboard_reference != original.plan.storyboard_reference
    assert changed.source_binding_sha256 != original.source_binding_sha256
    assert changed.plan.plan_id != original.plan.plan_id
    assert changed.plan.panels[0].panel_id != original.plan.panels[0].panel_id


def test_page_id_is_derived_and_separate_or_alias_input_is_rejected(
    tmp_path: Path,
) -> None:
    source = _snapshot(tmp_path)
    repository, snapshot = source
    assert _convert(tmp_path, source).plan.page_id == "1"
    with pytest.raises(TypeError):
        _convert_revisioned_page_snapshot(
            repository,
            snapshot,
            page_number=1,
            page_id="01",  # type: ignore[call-arg]
            layout_profile_id="md-page-compositor-v1",
            layout_profile_version=1,
            rectangles=(_rectangle(),),
        )


@pytest.mark.parametrize("page_number", [True, 0, -1, "01"])
def test_page_number_must_be_a_strict_positive_integer(tmp_path: Path, page_number: object) -> None:
    with pytest.raises(ValueError, match="page_number"):
        _convert(tmp_path, page_number=page_number)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "numbers",
    [
        [True],
        [0],
        [2],
        [1, 1],
        [1, 3],
        [2, 1],
    ],
)
def test_panel_numbers_must_be_strict_contiguous_and_persisted_ordered(
    tmp_path: Path,
    numbers: list[object],
) -> None:
    panels = [_panel(number=number) for number in numbers]
    rectangles = tuple(
        _rectangle(50_000 + index * 500_000, 450_000 + index * 500_000)
        for index in range(len(numbers))
    )
    with pytest.raises(ValueError, match="panel numbers"):
        _convert(
            tmp_path,
            _snapshot(tmp_path, storyboard={"panels": panels}),
            rectangles=rectangles,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda panel: panel.pop("narrative_intent"),
        lambda panel: panel.pop("characters"),
        lambda panel: panel.pop("continuity_bindings"),
        lambda panel: panel.pop("action"),
        lambda panel: panel.pop("background"),
        lambda panel: panel.pop("composition"),
        lambda panel: panel.pop("constraints"),
    ],
)
def test_missing_explicit_panel_fields_fail_closed(
    tmp_path: Path,
    mutation: Callable[[dict[str, object]], object],
) -> None:
    panel = _panel()
    mutation(panel)
    with pytest.raises(ValueError, match="requires explicit"):
        _convert(tmp_path, _snapshot(tmp_path, storyboard={"panels": [panel]}))


def test_missing_layout_or_rectangle_fails_closed(tmp_path: Path) -> None:
    repository, snapshot = _snapshot(tmp_path)
    with pytest.raises(TypeError):
        _convert_revisioned_page_snapshot(  # type: ignore[call-arg]
            repository,
            snapshot,
            page_number=1,
            layout_profile_id="md-page-compositor-v1",
            layout_profile_version=1,
        )
    with pytest.raises(ValueError, match="exactly one rectangle"):
        _convert(tmp_path, (repository, snapshot), rectangles=())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("characters", ["protagonist"]),
        ("action", "advance the page purpose"),
    ],
)
def test_existing_v7_13_prompt_validation_rejects_abstract_values(
    tmp_path: Path, field: str, value: object
) -> None:
    with pytest.raises(ValidationError):
        _convert(
            tmp_path,
            _snapshot(tmp_path, storyboard={"panels": [_panel(**{field: value})]}),
        )


def test_character_identities_must_be_an_explicit_nonempty_ordered_list(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="non-empty ordered string list"):
        _convert(
            tmp_path,
            _snapshot(tmp_path, storyboard={"panels": [_panel(characters=[])]}),
        )


@pytest.mark.parametrize(
    "prompt",
    [
        {},
        {"prompt_markdown": None},
        {"prompt_markdown": 123},
        {"prompt_markdown": ["not", "a", "string"]},
    ],
)
def test_prompt_built_requires_exact_prompt_markdown_string(
    tmp_path: Path,
    prompt: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="prompt_markdown"):
        _convert(tmp_path, _snapshot(tmp_path, prompt=prompt))


@pytest.mark.parametrize(
    ("profile_id", "profile_version"),
    [("other-profile", 1), ("md-page-compositor-v1", 2), ("md-page-compositor-v1", True)],
)
def test_layout_profile_and_version_mismatch_is_rejected(
    tmp_path: Path,
    profile_id: str,
    profile_version: object,
) -> None:
    with pytest.raises(ValueError, match="layout profile"):
        _convert(
            tmp_path,
            layout_profile_id=profile_id,
            layout_profile_version=profile_version,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "rectangles",
    [
        (_rectangle(1, 2),),
        (PanelRectangle(left=0, top=40_000, right=450_000, bottom=960_000),),
        (_rectangle(50_000, 600_000), _rectangle(500_000, 950_000)),
        (_rectangle(50_000, 450_000), _rectangle(460_000, 950_000)),
    ],
)
def test_existing_v7_13_geometry_validation_rejects_invalid_layout(
    tmp_path: Path,
    rectangles: tuple[PanelRectangle, ...],
) -> None:
    panels = [_panel(number=index) for index in range(1, len(rectangles) + 1)]
    with pytest.raises(ValidationError):
        _convert(
            tmp_path,
            _snapshot(tmp_path, storyboard={"panels": panels}),
            rectangles=rectangles,
        )


def test_malformed_rectangle_is_rejected_by_existing_v7_13_validator() -> None:
    with pytest.raises(ValidationError):
        PanelRectangle(left=True, top=40_000, right=950_000, bottom=960_000)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("left", 50_000.5),
        ("left", -1),
        ("top", -1),
        ("right", 1_000_001),
        ("bottom", 1_000_001),
    ],
)
def test_unvalidated_rectangle_model_copy_fails_closed_at_converter_boundary(
    tmp_path: Path, field: str, value: int | float
) -> None:
    rectangle = _rectangle().model_copy(update={field: value})

    with pytest.raises(ValidationError):
        _convert(tmp_path, rectangles=(rectangle,))


def test_unmapped_storyboard_fields_are_never_used_for_missing_values(
    tmp_path: Path,
) -> None:
    panel = _panel(
        role="A substituted narrative intent",
        camera="A substituted composition",
        dialogue=["A substituted action"],
    )
    panel.pop("narrative_intent")
    panel.pop("composition")
    panel.pop("action")

    with pytest.raises(ValueError, match="requires explicit"):
        _convert(tmp_path, _snapshot(tmp_path, storyboard={"panels": [panel]}))


def test_snapshot_revision_and_fingerprint_mismatch_is_rejected(tmp_path: Path) -> None:
    repository, snapshot = _snapshot(tmp_path)

    with pytest.raises(ValueError, match="does not match LocalFile authority"):
        _convert_revisioned_page_snapshot(
            repository,
            replace(snapshot, revision=snapshot.revision + 1),
            page_number=1,
            layout_profile_id="md-page-compositor-v1",
            layout_profile_version=1,
            rectangles=(_rectangle(),),
        )
    with pytest.raises(ValueError, match="does not match LocalFile authority"):
        _convert_revisioned_page_snapshot(
            repository,
            replace(snapshot, fingerprint="e" * 64),
            page_number=1,
            layout_profile_id="md-page-compositor-v1",
            layout_profile_version=1,
            rectangles=(_rectangle(),),
        )


def test_mutated_snapshot_artifacts_cannot_retain_authoritative_binding(
    tmp_path: Path,
) -> None:
    repository, snapshot = _snapshot(tmp_path)
    storyboard = cast(dict[str, object], snapshot.project.page(1).storyboard)
    panels = cast(list[object], storyboard["panels"])
    panel = cast(dict[str, object], panels[0])
    panel["action"] = "This change was never persisted."

    with pytest.raises(ValueError, match="does not match LocalFile authority"):
        _convert_revisioned_page_snapshot(
            repository,
            snapshot,
            page_number=1,
            layout_profile_id="md-page-compositor-v1",
            layout_profile_version=1,
            rectangles=(_rectangle(),),
        )


@pytest.mark.parametrize("source_page_number", [True, 1.0])
def test_source_page_number_must_be_an_exact_positive_integer(
    tmp_path: Path, source_page_number: object
) -> None:
    _, snapshot = _snapshot(tmp_path)
    page = snapshot.project.page(1).model_copy(update={"page_number": source_page_number})
    project = snapshot.project.model_copy(update={"pages": [page]})

    with pytest.raises(ValueError, match="requested PromptBuilt Page"):
        _snapshot_page_binding(replace(snapshot, project=project), 1)
