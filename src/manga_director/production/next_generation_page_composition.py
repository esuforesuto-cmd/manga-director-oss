"""Pure contracts for complete-set deterministic Page composition."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_page_generation_plan import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    COMPOSITOR_PROFILE_ID,
    MIN_GUTTER_PX,
    MIN_MARGIN_PX,
    PanelRectangle,
    canonical_digest,
    logical_reference,
    sha256_digest,
    validate_geometry,
)


class _CompositionModel(DirectorModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, validate_default=True
    )


class AcceptedPanelSource(_CompositionModel):
    plan_id: str
    plan_fingerprint: str
    project_id: str
    page_id: str
    panel_id: str
    panel_order: int = Field(ge=1, le=16)
    request_id: str
    request_fingerprint: str
    attempt_id: str
    evidence_id: str
    asset_id: str
    content_sha256: str
    width: int = Field(gt=0, le=4096)
    height: int = Field(gt=0, le=4096)
    media_type: Literal["image/png"] = "image/png"
    rectangle: PanelRectangle

    @field_validator(
        "plan_id",
        "project_id",
        "page_id",
        "panel_id",
        "request_id",
        "attempt_id",
        "evidence_id",
        "asset_id",
        mode="before",
    )
    @classmethod
    def _references(cls, value: object) -> str:
        return logical_reference(value, "composition source reference")

    @field_validator("plan_fingerprint", "request_fingerprint", "content_sha256")
    @classmethod
    def _sha256(cls, value: str) -> str:
        return sha256_digest(value)


class PageCompositionRequest(_CompositionModel):
    composition_attempt_id: str
    plan_id: str
    plan_fingerprint: str
    project_id: str
    page_id: str
    source_state: Literal["PromptBuilt"] = "PromptBuilt"
    target_state: Literal["Generated"] = "Generated"
    explicit_authorization_reference: str
    composition_provenance_reference: str
    compositor_profile_id: Literal["md-page-compositor-v1"] = COMPOSITOR_PROFILE_ID
    compositor_profile_version: Literal[1] = 1
    canvas_width: Literal[2048] = CANVAS_WIDTH
    canvas_height: Literal[3072] = CANVAS_HEIGHT
    margins: tuple[int, int, int, int] = (
        MIN_MARGIN_PX,
        MIN_MARGIN_PX,
        MIN_MARGIN_PX,
        MIN_MARGIN_PX,
    )
    gutter_px: int = Field(default=MIN_GUTTER_PX, ge=MIN_GUTTER_PX)
    pixel_fit_policy: Literal["cover-center"] = "cover-center"
    color_policy: Literal["srgb-rgba-on-white-v1"] = "srgb-rgba-on-white-v1"
    encoder_profile: Literal["rgb8-png-stored-deflate-v1"] = (
        "rgb8-png-stored-deflate-v1"
    )
    panel_count: int = Field(ge=1, le=16)
    sources: tuple[AcceptedPanelSource, ...] = Field(min_length=1, max_length=16)
    request_fingerprint: str | None = None

    @field_validator(
        "composition_attempt_id",
        "plan_id",
        "project_id",
        "page_id",
        "explicit_authorization_reference",
        "composition_provenance_reference",
        mode="before",
    )
    @classmethod
    def _logical_reference(cls, value: object) -> str:
        return logical_reference(value, "composition reference")

    @field_validator("plan_fingerprint")
    @classmethod
    def _plan_hash(cls, value: str) -> str:
        return sha256_digest(value)

    @field_validator("margins")
    @classmethod
    def _margins(cls, value: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        if len(value) != 4 or any(item < MIN_MARGIN_PX for item in value):
            raise ValueError("all composition margins must be at least 96 pixels")
        if value[1] + value[3] >= CANVAS_WIDTH or value[0] + value[2] >= CANVAS_HEIGHT:
            raise ValueError("composition margins must leave a positive content area")
        return value

    @model_validator(mode="after")
    def _canonical_complete_sources(self) -> PageCompositionRequest:
        if len(self.sources) != self.panel_count:
            raise ValueError("sources must contain the plan's complete Panel set")
        _validate_source_manifest(self.sources)
        for source in self.sources:
            if (
                source.plan_id != self.plan_id
                or source.plan_fingerprint != self.plan_fingerprint
                or source.project_id != self.project_id
                or source.page_id != self.page_id
            ):
                raise ValueError("every source must match the exact plan and Page binding")
        validate_geometry(
            tuple(source.rectangle for source in self.sources),
            self.canvas_width,
            self.canvas_height,
            self.margins,
            self.gutter_px,
        )
        if sum(source.width * source.height for source in self.sources) > 32_000_000:
            raise ValueError("source manifest exceeds the aggregate pixel limit")
        expected = canonical_digest(
            self.model_dump(mode="json", exclude={"request_fingerprint"})
        )
        if self.request_fingerprint is not None and self.request_fingerprint != expected:
            raise ValueError("request fingerprint does not match composition inputs")
        object.__setattr__(self, "request_fingerprint", expected)
        return self


class PageCompositionAttempt(_CompositionModel):
    """One local deterministic composition operation; never a Provider attempt."""

    composition_attempt_id: str
    request_fingerprint: str
    plan_id: str
    plan_fingerprint: str
    project_id: str
    page_id: str
    explicit_authorization_reference: str
    composition_provenance_reference: str
    compositor_profile_id: Literal["md-page-compositor-v1"] = COMPOSITOR_PROFILE_ID
    compositor_profile_version: Literal[1] = 1
    ordered_source_asset_ids: tuple[str, ...] = Field(min_length=1, max_length=16)
    ordered_source_hashes: tuple[str, ...] = Field(min_length=1, max_length=16)
    outcome: Literal["reserved", "completed", "failed", "recovery_required"] = "reserved"

    @field_validator(
        "composition_attempt_id",
        "plan_id",
        "project_id",
        "page_id",
        "explicit_authorization_reference",
        "composition_provenance_reference",
        mode="before",
    )
    @classmethod
    def _attempt_references(cls, value: object) -> str:
        return logical_reference(value, "composition attempt reference")

    @field_validator("ordered_source_asset_ids")
    @classmethod
    def _source_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        validated = tuple(logical_reference(value, "source asset") for value in values)
        if len(set(validated)) != len(validated):
            raise ValueError("composition source assets must be unique")
        return validated

    @field_validator("request_fingerprint", "plan_fingerprint")
    @classmethod
    def _attempt_digest(cls, value: str) -> str:
        return sha256_digest(value)

    @field_validator("ordered_source_hashes")
    @classmethod
    def _source_hashes(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sha256_digest(value) for value in values)

    @model_validator(mode="after")
    def _same_source_cardinality(self) -> PageCompositionAttempt:
        if len(self.ordered_source_asset_ids) != len(self.ordered_source_hashes):
            raise ValueError("composition source IDs and hashes must have equal cardinality")
        return self


class PageCompositionEvidence(_CompositionModel):
    evidence_id: str
    composition_attempt_id: str
    plan_id: str
    plan_fingerprint: str
    project_id: str
    page_id: str
    request_fingerprint: str
    operation_kind: Literal["deterministic_page_composition"] = "deterministic_page_composition"
    provider_invocation_performed: Literal[False] = False
    composition_provenance_reference: str
    compositor_profile_id: Literal["md-page-compositor-v1"] = COMPOSITOR_PROFILE_ID
    compositor_profile_version: Literal[1] = 1
    ordered_sources: tuple[AcceptedPanelSource, ...] = Field(min_length=1, max_length=16)
    output_asset_id: str | None = None
    output_sha256: str | None = None
    outcome: Literal["completed", "failed", "recovery_required"]

    @field_validator(
        "composition_attempt_id",
        "evidence_id",
        "plan_id",
        "project_id",
        "page_id",
        "composition_provenance_reference",
        mode="before",
    )
    @classmethod
    def _references(cls, value: object) -> str:
        return logical_reference(value, "composition evidence reference")

    @field_validator("output_asset_id")
    @classmethod
    def _output_reference(cls, value: str | None) -> str | None:
        return None if value is None else logical_reference(value, "composite asset")

    @field_validator("plan_fingerprint", "request_fingerprint")
    @classmethod
    def _evidence_digests(cls, value: str) -> str:
        return sha256_digest(value)

    @field_validator("output_sha256")
    @classmethod
    def _output_digest(cls, value: str | None) -> str | None:
        return None if value is None else sha256_digest(value)

    @model_validator(mode="after")
    def _terminal_binding(self) -> PageCompositionEvidence:
        _validate_source_manifest(self.ordered_sources)
        for source in self.ordered_sources:
            if (
                source.plan_id != self.plan_id
                or source.plan_fingerprint != self.plan_fingerprint
                or source.project_id != self.project_id
                or source.page_id != self.page_id
            ):
                raise ValueError("evidence sources must match its exact plan and Page")
        if self.outcome == "completed":
            if self.output_asset_id is None or self.output_sha256 is None:
                raise ValueError("completed composition evidence requires one output")
        elif self.output_asset_id is not None or self.output_sha256 is not None:
            raise ValueError("non-success composition evidence cannot name an output")
        return self


class PageCompositeAsset(_CompositionModel):
    """Registered deterministic Page output and its complete source manifest."""

    composition_attempt_id: str
    request_fingerprint: str
    composition_provenance_reference: str
    ordered_sources: tuple[AcceptedPanelSource, ...] = Field(min_length=1, max_length=16)
    asset_id: str
    width: Literal[2048] = CANVAS_WIDTH
    height: Literal[3072] = CANVAS_HEIGHT
    media_type: Literal["image/png"] = "image/png"
    content_sha256: str

    @field_validator(
        "composition_attempt_id",
        "composition_provenance_reference",
        "asset_id",
        mode="before",
    )
    @classmethod
    def _asset_references(cls, value: object) -> str:
        return logical_reference(value, "composite asset reference")

    @field_validator("request_fingerprint", "content_sha256")
    @classmethod
    def _asset_digests(cls, value: str) -> str:
        return sha256_digest(value)

    @model_validator(mode="after")
    def _canonical_source_manifest(self) -> PageCompositeAsset:
        _validate_source_manifest(self.ordered_sources)
        bindings = {
            (
                source.plan_id,
                source.plan_fingerprint,
                source.project_id,
                source.page_id,
            )
            for source in self.ordered_sources
        }
        if len(bindings) != 1:
            raise ValueError("composite sources must share one exact plan and Page binding")
        return self


def _validate_source_manifest(sources: tuple[AcceptedPanelSource, ...]) -> None:
    if [source.panel_order for source in sources] != list(range(1, len(sources) + 1)):
        raise ValueError("sources must remain in canonical contiguous Panel order")
    unique_fields = {
        "Panel IDs": (source.panel_id for source in sources),
        "request IDs": (source.request_id for source in sources),
        "attempt IDs": (source.attempt_id for source in sources),
        "evidence IDs": (source.evidence_id for source in sources),
        "asset IDs": (source.asset_id for source in sources),
    }
    for label, values in unique_fields.items():
        resolved = tuple(values)
        if len(set(resolved)) != len(resolved):
            raise ValueError(f"source {label} must be unique")


CompositionAuthorityOutcome = Literal[
    "created", "updated", "confirmed", "missing", "conflict", "corrupt", "failed"
]

_COMPOSITION_DATABASE = "page-composition-authority.sqlite3"
_COMPOSITION_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class PageCompositionAuthorityResult:
    composition_attempt_id: str
    outcome: CompositionAuthorityOutcome
    attempt: PageCompositionAttempt | None = field(default=None, repr=False)
    evidence: PageCompositionEvidence | None = field(default=None, repr=False)


@dataclass(frozen=True, slots=True)
class PageCompositionPageObservation:
    outcome: Literal["found", "missing", "corrupt", "ambiguous"]
    plan_ids: tuple[str, ...] = ()
    attempt_ids: tuple[str, ...] = ()
    asset_required_attempt_ids: tuple[str, ...] = ()
    attempts: tuple[PageCompositionAttempt, ...] = field(default=(), repr=False)
    evidence: tuple[PageCompositionEvidence, ...] = field(default=(), repr=False)


class LocalPageCompositionAuthority:
    """Private versioned store for deterministic attempts and immutable evidence."""

    def __init__(self, owner_root: Path) -> None:
        self._root = _prepare_composition_root(owner_root)
        self._database_path = _prepare_composition_database(self._root)
        self._initialize_schema()

    def reserve(
        self, request: PageCompositionRequest
    ) -> PageCompositionAuthorityResult:
        attempt = PageCompositionAttempt(
            composition_attempt_id=request.composition_attempt_id,
            request_fingerprint=request.request_fingerprint or "",
            plan_id=request.plan_id,
            plan_fingerprint=request.plan_fingerprint,
            project_id=request.project_id,
            page_id=request.page_id,
            explicit_authorization_reference=request.explicit_authorization_reference,
            composition_provenance_reference=request.composition_provenance_reference,
            compositor_profile_id=request.compositor_profile_id,
            compositor_profile_version=request.compositor_profile_version,
            ordered_source_asset_ids=tuple(source.asset_id for source in request.sources),
            ordered_source_hashes=tuple(source.content_sha256 for source in request.sources),
        )
        payload = _composition_json(attempt)
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT composition_attempt_id, project_id, page_id, plan_id, outcome, "
                "payload_json, payload_digest FROM composition_attempts "
                "WHERE composition_attempt_id = ?",
                (attempt.composition_attempt_id,),
            ).fetchone()
            if row is not None:
                connection.rollback()
                existing = _validated_attempt(row)
                if existing is None:
                    return _composition_result(attempt, "corrupt")
                return _composition_result(
                    existing, "confirmed" if existing == attempt else "conflict"
                )
            active = connection.execute(
                "SELECT composition_attempt_id, project_id, page_id, plan_id, outcome, "
                "payload_json, payload_digest FROM composition_attempts",
            ).fetchall()
            verified = tuple(_validated_attempt(item) for item in active)
            if any(item is None for item in verified):
                connection.rollback()
                return _composition_result(attempt, "corrupt")
            if any(
                item is not None
                and item.project_id == attempt.project_id
                and item.page_id == attempt.page_id
                and (
                    item.plan_id != attempt.plan_id
                    or item.plan_fingerprint != attempt.plan_fingerprint
                )
                for item in verified
            ):
                connection.rollback()
                return _composition_result(attempt, "conflict")
            if any(
                item is not None
                and item.project_id == attempt.project_id
                and item.page_id == attempt.page_id
                and item.outcome in {"reserved", "recovery_required"}
                for item in verified
            ):
                connection.rollback()
                return _composition_result(attempt, "conflict")
            connection.execute(
                "INSERT INTO composition_attempts VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    attempt.composition_attempt_id,
                    attempt.project_id,
                    attempt.page_id,
                    attempt.plan_id,
                    attempt.outcome,
                    payload,
                    _composition_digest(payload),
                ),
            )
            connection.commit()
            return _composition_result(attempt, "created")
        except sqlite3.IntegrityError:
            if connection is not None:
                _composition_rollback(connection)
            return _composition_result(attempt, "conflict")
        except Exception:
            if connection is not None:
                _composition_rollback(connection)
            return _composition_result(attempt, "failed")
        finally:
            if connection is not None:
                connection.close()

    def commit_evidence(
        self, evidence: PageCompositionEvidence
    ) -> PageCompositionAuthorityResult:
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT composition_attempt_id, project_id, page_id, plan_id, outcome, "
                "payload_json, payload_digest FROM composition_attempts "
                "WHERE composition_attempt_id = ?",
                (evidence.composition_attempt_id,),
            ).fetchone()
            if row is None:
                connection.rollback()
                return PageCompositionAuthorityResult(
                    evidence.composition_attempt_id, "missing"
                )
            attempt = _validated_attempt(row)
            if attempt is None:
                connection.rollback()
                return PageCompositionAuthorityResult(
                    evidence.composition_attempt_id, "corrupt"
                )
            if not _composition_evidence_matches(attempt, evidence):
                connection.rollback()
                return _composition_result(attempt, "conflict")
            existing_row = connection.execute(
                "SELECT composition_attempt_id, evidence_id, payload_json, payload_digest "
                "FROM composition_evidence "
                "WHERE composition_attempt_id = ?",
                (evidence.composition_attempt_id,),
            ).fetchone()
            if existing_row is not None:
                connection.rollback()
                existing_evidence = _validated_composition_evidence(existing_row)
                if existing_evidence is None:
                    return _composition_result(attempt, "corrupt")
                if existing_evidence == evidence:
                    return PageCompositionAuthorityResult(
                        attempt.composition_attempt_id,
                        "confirmed",
                        attempt,
                        existing_evidence,
                    )
                return _composition_result(attempt, "conflict")
            if attempt.outcome != "reserved":
                connection.rollback()
                return _composition_result(attempt, "conflict")
            target = {
                "completed": "completed",
                "failed": "failed",
                "recovery_required": "recovery_required",
            }[evidence.outcome]
            final_attempt = attempt.model_copy(update={"outcome": target})
            evidence_payload = _composition_json(evidence)
            attempt_payload = _composition_json(final_attempt)
            connection.execute(
                "INSERT INTO composition_evidence VALUES (?, ?, ?, ?)",
                (
                    evidence.composition_attempt_id,
                    evidence.evidence_id,
                    evidence_payload,
                    _composition_digest(evidence_payload),
                ),
            )
            connection.execute(
                "UPDATE composition_attempts SET outcome = ?, payload_json = ?, payload_digest = ? "
                "WHERE composition_attempt_id = ?",
                (
                    final_attempt.outcome,
                    attempt_payload,
                    _composition_digest(attempt_payload),
                    final_attempt.composition_attempt_id,
                ),
            )
            connection.commit()
            return PageCompositionAuthorityResult(
                final_attempt.composition_attempt_id,
                "updated",
                final_attempt,
                evidence,
            )
        except Exception:
            if connection is not None:
                _composition_rollback(connection)
            return PageCompositionAuthorityResult(
                evidence.composition_attempt_id, "failed"
            )
        finally:
            if connection is not None:
                connection.close()

    def lookup(self, composition_attempt_id: str) -> PageCompositionAuthorityResult:
        try:
            resolved = logical_reference(composition_attempt_id, "composition attempt")
        except ValueError:
            return PageCompositionAuthorityResult("", "corrupt")
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            attempt_row = connection.execute(
                "SELECT composition_attempt_id, project_id, page_id, plan_id, outcome, "
                "payload_json, payload_digest FROM composition_attempts "
                "WHERE composition_attempt_id = ?",
                (resolved,),
            ).fetchone()
            if attempt_row is None:
                return PageCompositionAuthorityResult(resolved, "missing")
            attempt = _validated_attempt(attempt_row)
            if attempt is None or attempt.composition_attempt_id != resolved:
                return PageCompositionAuthorityResult(resolved, "corrupt")
            evidence_row = connection.execute(
                "SELECT composition_attempt_id, evidence_id, payload_json, payload_digest "
                "FROM composition_evidence "
                "WHERE composition_attempt_id = ?",
                (resolved,),
            ).fetchone()
            evidence = (
                None
                if evidence_row is None
                else _validated_composition_evidence(evidence_row)
            )
            if evidence_row is not None and evidence is None:
                return PageCompositionAuthorityResult(resolved, "corrupt")
            if evidence is not None and not _composition_evidence_matches(attempt, evidence):
                return PageCompositionAuthorityResult(resolved, "corrupt")
            if (attempt.outcome == "reserved") != (evidence is None):
                return PageCompositionAuthorityResult(resolved, "corrupt")
            return PageCompositionAuthorityResult(
                resolved, "confirmed", attempt, evidence
            )
        except Exception:
            return PageCompositionAuthorityResult(resolved, "corrupt")
        finally:
            if connection is not None:
                connection.close()

    def observe_page(  # noqa: C901 - one closed authority integrity inventory.
        self, project_id: str, page_id: str
    ) -> PageCompositionPageObservation:
        """Read one Page's exact composition inventory without mutation."""

        path_status = _readonly_composition_status(self._root, self._database_path)
        if path_status == "missing":
            return PageCompositionPageObservation("missing")
        if path_status == "corrupt":
            return PageCompositionPageObservation("corrupt")
        try:
            uri = f"{self._database_path.as_uri()}?mode=ro"
            with sqlite3.connect(uri, uri=True) as connection:
                connection.execute("PRAGMA query_only = ON")
                if int(connection.execute("PRAGMA user_version").fetchone()[0]) != _COMPOSITION_SCHEMA_VERSION:
                    return PageCompositionPageObservation("corrupt")
                attempt_columns = tuple(
                    (str(row[1]), str(row[2]).upper(), int(row[3]), row[4], int(row[5]))
                    for row in connection.execute("PRAGMA table_info(composition_attempts)")
                )
                evidence_columns = tuple(
                    (str(row[1]), str(row[2]).upper(), int(row[3]), row[4], int(row[5]))
                    for row in connection.execute("PRAGMA table_info(composition_evidence)")
                )
                if not _composition_schema_objects_are_exact(connection) or attempt_columns != (
                    ("composition_attempt_id", "TEXT", 0, None, 1),
                    ("project_id", "TEXT", 1, None, 0),
                    ("page_id", "TEXT", 1, None, 0),
                    ("plan_id", "TEXT", 1, None, 0),
                    ("outcome", "TEXT", 1, None, 0),
                    ("payload_json", "TEXT", 1, None, 0),
                    ("payload_digest", "TEXT", 1, None, 0),
                ) or evidence_columns != (
                    ("composition_attempt_id", "TEXT", 0, None, 1),
                    ("evidence_id", "TEXT", 1, None, 0),
                    ("payload_json", "TEXT", 1, None, 0),
                    ("payload_digest", "TEXT", 1, None, 0),
                ):
                    return PageCompositionPageObservation("corrupt")
                attempt_rows = connection.execute(
                    "SELECT composition_attempt_id, project_id, page_id, plan_id, outcome, "
                    "payload_json, payload_digest FROM composition_attempts"
                ).fetchall()
                evidence_rows = connection.execute(
                    "SELECT composition_attempt_id, evidence_id, payload_json, payload_digest "
                    "FROM composition_evidence"
                ).fetchall()
            attempts = tuple(_validated_attempt(row) for row in attempt_rows)
            evidence = tuple(
                _validated_composition_evidence(row) for row in evidence_rows
            )
            if any(item is None for item in (*attempts, *evidence)):
                return PageCompositionPageObservation("corrupt")
            attempt_by_id = {
                item.composition_attempt_id: item
                for item in attempts
                if item is not None
            }
            if len(attempt_by_id) != len(attempts):
                return PageCompositionPageObservation("ambiguous")
            for item in evidence:
                assert item is not None
                attempt = attempt_by_id.get(item.composition_attempt_id)
                if (
                    attempt is None
                    or attempt.outcome != item.outcome
                    or not _composition_evidence_matches(attempt, item)
                ):
                    return PageCompositionPageObservation("corrupt")
            evidence_attempt_ids = {
                item.composition_attempt_id for item in evidence if item is not None
            }
            if any(
                (attempt.outcome != "reserved")
                != (attempt.composition_attempt_id in evidence_attempt_ids)
                for attempt in attempt_by_id.values()
            ):
                return PageCompositionPageObservation("corrupt")
            page_attempts = tuple(
                item
                for item in attempts
                if item is not None
                and item.project_id == project_id
                and item.page_id == page_id
            )
        except Exception:
            return PageCompositionPageObservation("corrupt")
        if not page_attempts:
            return PageCompositionPageObservation("missing")
        plans = tuple(sorted({item.plan_id for item in page_attempts}))
        attempt_ids = tuple(
            sorted(item.composition_attempt_id for item in page_attempts)
        )
        asset_required = tuple(
            sorted(
                item.composition_attempt_id
                for item in page_attempts
                if item.outcome == "completed"
            )
        )
        if len(plans) != 1:
            return PageCompositionPageObservation(
                "ambiguous", plans, attempt_ids, asset_required, page_attempts, ()
            )
        page_evidence = tuple(
            sorted(
                (
                    item
                    for item in evidence
                    if item is not None
                    and item.composition_attempt_id in attempt_ids
                ),
                key=lambda item: item.composition_attempt_id,
            )
        )
        return PageCompositionPageObservation(
            "found", plans, attempt_ids, asset_required, page_attempts, page_evidence
        )

    @classmethod
    def observe_page_at(
        cls, owner_root: Path, project_id: str, page_id: str
    ) -> PageCompositionPageObservation:
        authority = object.__new__(cls)
        authority._root = owner_root
        authority._database_path = owner_root / _COMPOSITION_DATABASE
        return authority.observe_page(project_id, page_id)

    def _initialize_schema(self) -> None:
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            connection.execute("BEGIN IMMEDIATE")
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                )
            }
            if version == 0 and not tables:
                connection.execute(
                    "CREATE TABLE composition_attempts (composition_attempt_id TEXT PRIMARY KEY, "
                    "project_id TEXT NOT NULL, page_id TEXT NOT NULL, plan_id TEXT NOT NULL, "
                    "outcome TEXT NOT NULL, payload_json TEXT NOT NULL, payload_digest TEXT NOT NULL)"
                )
                connection.execute(
                    "CREATE UNIQUE INDEX one_reserved_composition ON composition_attempts(project_id, page_id) "
                    "WHERE outcome IN ('reserved', 'recovery_required')"
                )
                connection.execute(
                    "CREATE TABLE composition_evidence (composition_attempt_id TEXT PRIMARY KEY, "
                    "evidence_id TEXT UNIQUE NOT NULL, payload_json TEXT NOT NULL, payload_digest TEXT NOT NULL)"
                )
                connection.execute(f"PRAGMA user_version = {_COMPOSITION_SCHEMA_VERSION}")
                connection.commit()
                return
            if version != _COMPOSITION_SCHEMA_VERSION or tables != {
                "composition_attempts", "composition_evidence"
            }:
                raise ValueError("composition authority is unavailable")
            connection.commit()
        except Exception as error:
            if connection is not None:
                _composition_rollback(connection)
            raise ValueError("composition authority is unavailable") from error
        finally:
            if connection is not None:
                connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5.0, isolation_level=None)
        mode = str(connection.execute("PRAGMA journal_mode = DELETE").fetchone()[0]).lower()
        if mode != "delete":
            connection.close()
            raise ValueError("composition authority is unavailable")
        connection.execute("PRAGMA synchronous = FULL")
        return connection


def _composition_evidence_matches(
    attempt: PageCompositionAttempt, evidence: PageCompositionEvidence
) -> bool:
    return (
        attempt.composition_attempt_id,
        attempt.request_fingerprint,
        attempt.plan_id,
        attempt.plan_fingerprint,
        attempt.project_id,
        attempt.page_id,
        attempt.composition_provenance_reference,
        attempt.compositor_profile_id,
        attempt.compositor_profile_version,
        attempt.ordered_source_asset_ids,
        attempt.ordered_source_hashes,
    ) == (
        evidence.composition_attempt_id,
        evidence.request_fingerprint,
        evidence.plan_id,
        evidence.plan_fingerprint,
        evidence.project_id,
        evidence.page_id,
        evidence.composition_provenance_reference,
        evidence.compositor_profile_id,
        evidence.compositor_profile_version,
        tuple(source.asset_id for source in evidence.ordered_sources),
        tuple(source.content_sha256 for source in evidence.ordered_sources),
    )


def _composition_result(
    attempt: PageCompositionAttempt, outcome: CompositionAuthorityOutcome
) -> PageCompositionAuthorityResult:
    return PageCompositionAuthorityResult(
        attempt.composition_attempt_id, outcome, attempt
    )


def _validated_attempt(row: object) -> PageCompositionAttempt | None:
    if not isinstance(row, tuple) or len(row) != 7:
        return None
    attempt_id, project_id, page_id, plan_id, outcome, payload, digest = row
    payload = _validated_composition_payload((payload, digest))
    if payload is None:
        return None
    try:
        attempt = PageCompositionAttempt.model_validate_json(payload)
    except Exception:
        return None
    if (
        attempt.composition_attempt_id != attempt_id
        or attempt.project_id != project_id
        or attempt.page_id != page_id
        or attempt.plan_id != plan_id
        or attempt.outcome != outcome
    ):
        return None
    return attempt


def _validated_composition_evidence(row: object) -> PageCompositionEvidence | None:
    if not isinstance(row, tuple) or len(row) != 4:
        return None
    attempt_id, evidence_id, payload, digest = row
    payload = _validated_composition_payload((payload, digest))
    if payload is None:
        return None
    try:
        evidence = PageCompositionEvidence.model_validate_json(payload)
    except Exception:
        return None
    if (
        evidence.composition_attempt_id != attempt_id
        or evidence.evidence_id != evidence_id
    ):
        return None
    return evidence


def _composition_schema_objects_are_exact(connection: sqlite3.Connection) -> bool:
    objects = connection.execute(
        "SELECT type, name, tbl_name FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
    ).fetchall()
    if objects != [
        ("index", "one_reserved_composition", "composition_attempts"),
        ("table", "composition_attempts", "composition_attempts"),
        ("table", "composition_evidence", "composition_evidence"),
    ]:
        return False
    expected: dict[str, set[tuple[int, str, int, tuple[str, ...]]]] = {
        "composition_attempts": {
            (1, "pk", 0, ("composition_attempt_id",)),
            (1, "c", 1, ("project_id", "page_id")),
        },
        "composition_evidence": {
            (1, "pk", 0, ("composition_attempt_id",)),
            (1, "u", 0, ("evidence_id",)),
        },
    }
    for table, expected_indexes in expected.items():
        observed: set[tuple[int, str, int, tuple[str, ...]]] = set()
        for index in connection.execute(f"PRAGMA index_list({table})").fetchall():
            if len(index) != 5 or not isinstance(index[1], str):
                return False
            columns = tuple(
                str(row[2])
                for row in connection.execute(
                    f"PRAGMA index_info({index[1]})"
                ).fetchall()
            )
            observed.add((int(index[2]), str(index[3]), int(index[4]), columns))
        if observed != expected_indexes:
            return False
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'index' "
        "AND name = 'one_reserved_composition'"
    ).fetchone()
    expected_sql = (
        "CREATE UNIQUE INDEX one_reserved_composition "
        "ON composition_attempts(project_id, page_id) "
        "WHERE outcome IN ('reserved', 'recovery_required')"
    )
    return bool(
        isinstance(row, tuple)
        and len(row) == 1
        and isinstance(row[0], str)
        and _without_ascii_whitespace(row[0]).lower()
        == _without_ascii_whitespace(expected_sql).lower()
    )


def _without_ascii_whitespace(value: str) -> str:
    return "".join(
        character for character in value if character not in " \t\r\n\f\v"
    )


def _readonly_composition_status(
    root: Path, database: Path
) -> Literal["found", "missing", "corrupt"]:
    try:
        root_kind = _readonly_path_kind(root)
        if root_kind == "missing":
            return "missing"
        parent = root.parent
        if (
            not root.is_absolute()
            or root_kind != "directory"
            or _readonly_path_kind(parent) != "directory"
        ):
            return "corrupt"
        if (
            _readonly_path_kind(database) != "file"
            or database.resolve(strict=True).parent != root.resolve(strict=True)
        ):
            return "corrupt"
        return "found"
    except OSError:
        return "corrupt"


def _readonly_path_kind(
    path: Path,
) -> Literal["missing", "file", "directory", "unsafe"]:
    try:
        status = path.lstat()
    except FileNotFoundError:
        return "missing"
    except OSError:
        return "unsafe"
    attributes = getattr(status, "st_file_attributes", 0)
    if stat.S_ISLNK(status.st_mode) or bool(
        attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    ):
        return "unsafe"
    if stat.S_ISREG(status.st_mode):
        return "file"
    if stat.S_ISDIR(status.st_mode):
        return "directory"
    return "unsafe"


def _validated_composition_payload(row: object) -> str | None:
    if not isinstance(row, tuple) or len(row) != 2:
        return None
    payload, digest = row
    if (
        not isinstance(payload, str)
        or not isinstance(digest, str)
        or _composition_digest(payload) != digest
    ):
        return None
    return payload


def _composition_json(model: _CompositionModel) -> str:
    return json.dumps(
        model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def _composition_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _prepare_composition_root(root: Path) -> Path:
    if not isinstance(root, Path) or root.is_symlink() or _composition_reparse(root):
        raise ValueError("composition authority root is unavailable")
    root.mkdir(parents=True, exist_ok=True)
    resolved = root.resolve(strict=True)
    if not resolved.is_dir() or resolved.is_symlink() or _composition_reparse(resolved):
        raise ValueError("composition authority root is unavailable")
    return resolved


def _prepare_composition_database(root: Path) -> Path:
    path = root / _COMPOSITION_DATABASE
    if path.exists() and (
        not path.is_file() or path.is_symlink() or _composition_reparse(path)
    ):
        raise ValueError("composition authority is unavailable")
    if path.resolve(strict=False).parent != root:
        raise ValueError("composition authority is unavailable")
    return path


def _composition_reparse(path: Path) -> bool:
    try:
        attributes = path.lstat()
        return bool(
            getattr(attributes, "st_file_attributes", 0)
            & stat.FILE_ATTRIBUTE_REPARSE_POINT
        )
    except (FileNotFoundError, OSError):
        return False


def _composition_rollback(connection: sqlite3.Connection) -> None:
    try:
        connection.rollback()
    except sqlite3.Error:
        pass
