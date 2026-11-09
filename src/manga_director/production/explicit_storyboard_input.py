"""Private contracts for explicitly confirmed storyboard panel input."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

from manga_director.domain.exceptions import ValidationError

_PANEL_KEYS = frozenset(
    {
        "number",
        "narrative_intent",
        "characters",
        "continuity_bindings",
        "action",
        "background",
        "composition",
        "constraints",
    }
)
_CONFIRMATION_KEYS = frozenset(
    {
        "schema_id",
        "schema_version",
        "source_project_id",
        "source_page_number",
        "source_sha256",
        "source_page_design_sha256",
        "source_review_sha256",
        "panel_input_sha256",
        "user_confirmed",
    }
)
_TEXT = frozenset({"narrative_intent", "action", "background", "composition"})
_LIST_LIMITS = {"characters": (1, 32), "continuity_bindings": (1, 32), "constraints": (1, 64)}
_CHARACTER_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z", re.ASCII)
_ABSTRACT = frozenset({
    "advance the page purpose", "character", "continue", "continuity",
    "protagonist", "same as above", "tbd",
})
_DIGEST = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


def canonical_json(value: object) -> bytes:
    try:
        _require_json_value(value)
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ValidationError("Storyboard confirmation contains unsupported JSON values.") from exc


def _require_json_value(value: object) -> None:
    if value is None or type(value) in (str, bool, int):
        if type(value) is str:
            value.encode("utf-8", errors="strict")
        return
    if type(value) is float:
        if value != value or value in (float("inf"), float("-inf")):
            raise ValidationError("Storyboard confirmation contains unsupported JSON values.")
        return
    if type(value) is list:
        for item in value:
            _require_json_value(item)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _require_json_value(item)
        return
    raise ValidationError("Storyboard confirmation contains unsupported JSON values.")


def sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def validate_panels(value: object) -> list[dict[str, Any]]:
    if type(value) is not list or not 1 <= len(value) <= 16:
        raise ValidationError("Storyboard must contain between 1 and 16 panels.")
    result: list[dict[str, Any]] = []
    for expected_number, panel in enumerate(value, 1):
        if type(panel) is not dict or set(panel) != _PANEL_KEYS:
            raise ValidationError("Each storyboard panel must use the exact supported fields.")
        number = panel["number"]
        if type(number) is not int or number != expected_number:
            raise ValidationError("Storyboard panel numbers must be contiguous and ordered.")
        normalized: dict[str, Any] = {"number": number}
        for key in _TEXT:
            normalized[key] = _validate_panel_text(panel[key])
        for key in _LIST_LIMITS:
            normalized[key] = _validate_panel_list(key, panel[key])
        result.append(normalized)
    return result


def _validate_panel_text(value: object) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value) > 4000
        or value.casefold() in _ABSTRACT
        or value.startswith(("# Storyboard", "```"))
        or not any(character.isalnum() for character in value)
    ):
        raise ValidationError("Storyboard panel text must be explicit, trimmed, and bounded.")
    return value


def _validate_panel_list(key: str, value: object) -> list[str]:
    minimum, maximum = _LIST_LIMITS[key]
    if type(value) is not list or not minimum <= len(value) <= maximum:
        raise ValidationError("Storyboard panel lists are empty or exceed supported bounds.")
    if any(
        type(item) is not str
        or not item
        or item != item.strip()
        or len(item) > 512
        or item.casefold() in _ABSTRACT
        for item in value
    ):
        raise ValidationError("Storyboard panel list values must be explicit and bounded.")
    items = cast(list[str], value)
    if key == "characters":
        if any(not _CHARACTER_ID.fullmatch(item) for item in items):
            raise ValidationError("Character references must be bounded logical identifiers.")
        if len(items) != len(set(items)):
            raise ValidationError("Character references cannot repeat within a panel.")
    return list(items)


def validate_expected_source(value: object) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {"state", "page_design", "review"}:
        raise ValidationError("Expected storyboard source must use the exact supported fields.")
    if value["state"] != "Reviewed" or type(value["state"]) is not str:
        raise ValidationError("Storyboard confirmation requires a Reviewed source.")
    if type(value["page_design"]) is not dict or type(value["review"]) is not dict:
        raise ValidationError("Expected source artifacts must be JSON objects.")
    # Round-trip through canonical JSON to reject values the API cannot preserve.
    return cast(dict[str, Any], json.loads(canonical_json(value)))


def reviewed_source(project_id: str, page_number: int, expected: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "kind": "reviewed_storyboard_source_v1",
        "version": 1,
        "project_id": project_id,
        "page_number": page_number,
        "source": {
            "state": "Reviewed",
            "page_design": expected["page_design"],
            "review": expected["review"],
        },
    }


@dataclass(frozen=True, slots=True)
class _ExplicitStoryboardInputAuthority:
    """Exact-type transient authority bound to a single fenced Reviewed snapshot."""

    project_id: str
    page_number: int
    revision: int
    fingerprint: str
    source_sha256: str
    page_design_sha256: str
    review_sha256: str
    panel_input_sha256: str
    panels_json: bytes

    @property
    def panels(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], json.loads(self.panels_json))


def create_authority(
    project_id: str,
    page_number: int,
    revision: int,
    fingerprint: str,
    source: Mapping[str, Any],
    panels: object,
) -> _ExplicitStoryboardInputAuthority:
    exact_panels = validate_panels(panels)
    source_projection = reviewed_source(project_id, page_number, source)
    return _ExplicitStoryboardInputAuthority(
        project_id=project_id,
        page_number=page_number,
        revision=revision,
        fingerprint=fingerprint,
        source_sha256=sha256(source_projection),
        page_design_sha256=sha256(source["page_design"]),
        review_sha256=sha256(source["review"]),
        panel_input_sha256=sha256(exact_panels),
        panels_json=canonical_json(exact_panels),
    )


def confirmation_record(authority: _ExplicitStoryboardInputAuthority) -> dict[str, Any]:
    return {
        "schema_id": "manga_director.explicit_storyboard_input",
        "schema_version": 1,
        "source_project_id": authority.project_id,
        "source_page_number": authority.page_number,
        "source_sha256": authority.source_sha256,
        "source_page_design_sha256": authority.page_design_sha256,
        "source_review_sha256": authority.review_sha256,
        "panel_input_sha256": authority.panel_input_sha256,
        "user_confirmed": True,
    }


def validate_confirmation(storyboard: object, project_id: str, page_number: int, artifacts: Mapping[str, Any]) -> None:
    if type(storyboard) is not dict or "confirmation" not in storyboard:
        return
    if set(storyboard) != {"panels", "confirmation"}:
        raise ValidationError("Confirmed storyboard has unsupported root fields.")
    page_design = artifacts.get("Designed")
    review = artifacts.get("Reviewed")
    if type(page_design) is not dict or type(review) is not dict:
        raise ValidationError("Confirmed storyboard source artifacts are missing or malformed.")
    confirmation = storyboard["confirmation"]
    if type(confirmation) is not dict or set(confirmation) != _CONFIRMATION_KEYS:
        raise ValidationError("Confirmed storyboard provenance is malformed.")
    panels = validate_panels(storyboard["panels"])
    expected = {
        "schema_id": "manga_director.explicit_storyboard_input",
        "schema_version": 1,
        "source_project_id": project_id,
        "source_page_number": page_number,
        "source_page_design_sha256": sha256(page_design),
        "source_review_sha256": sha256(review),
        "panel_input_sha256": sha256(panels),
        "user_confirmed": True,
    }
    for key, value in expected.items():
        if type(confirmation.get(key)) is not type(value) or confirmation.get(key) != value:
            raise ValidationError("Confirmed storyboard provenance no longer matches its source.")
    if not all(type(confirmation[key]) is str and _DIGEST.fullmatch(confirmation[key]) for key in ("source_sha256", "source_page_design_sha256", "source_review_sha256", "panel_input_sha256")):
        raise ValidationError("Confirmed storyboard provenance digest is malformed.")
    source = reviewed_source(
        project_id,
        page_number,
        {"page_design": page_design, "review": review},
    )
    if confirmation["source_sha256"] != sha256(source):
        raise ValidationError("Confirmed storyboard source no longer matches its provenance.")
