"""Read-only v5.6 Character Engine v1 for a single existing manga page.

The module projects supplied character, story, world, and timeline evidence
into consistency checks. It never changes an approved character profile,
relationship, arc, appearance, dialogue, repository, or workflow state.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal

from manga_director.production.director import DirectorModel
from manga_director.workflow.contracts import WorkflowContext

EvidenceStatus = Literal["ready", "needs_evidence"]


class CharacterRegistryDTO(DirectorModel):
    """Read-only character registry projection for exactly one existing page."""

    project_id: str
    page_reference: str
    character_ids: tuple[str, ...] = ()
    active_character_id: str | None = None
    registry_evidence_available: bool
    page_count: Literal[1] = 1
    registry_changed: Literal[False] = False


class CharacterProfileDTO(DirectorModel):
    """Profile evidence needed to preserve a character's approved identity."""

    character_id: str | None = None
    name_available: bool
    motivation_available: bool
    story_context_available: bool
    world_context_available: bool
    profile_valid: bool
    status: EvidenceStatus
    profile_changed: Literal[False] = False


class RelationshipGraphDTO(DirectorModel):
    """Relationship references validated only against supplied registry evidence."""

    nodes: tuple[str, ...] = ()
    edges: tuple[tuple[str, str, str], ...] = ()
    relationships_valid: bool
    status: EvidenceStatus
    graph_changed: Literal[False] = False


class CharacterArcManagerDTO(DirectorModel):
    """Character-growth evidence without changing the arc or its current stage."""

    goal_available: bool
    stage_available: bool
    timeline_context_available: bool
    arc_valid: bool
    status: EvidenceStatus
    arc_changed: Literal[False] = False


class AppearanceConsistencyDTO(DirectorModel):
    """Visual identity evidence for human art and continuity review."""

    hair_available: bool
    eyes_available: bool
    clothing_available: bool
    accessories_available: bool
    appearance_valid: bool
    status: EvidenceStatus
    appearance_changed: Literal[False] = False


class DialogueVoiceProfileDTO(DirectorModel):
    """Dialogue-voice evidence without writing or editing dialogue."""

    style_available: bool
    marker_count: int
    voice_valid: bool
    status: EvidenceStatus
    dialogue_changed: Literal[False] = False


class CharacterPromptBriefDTO(DirectorModel):
    """Compact prompt constraints that reuse approved character evidence by key."""

    page_reference: str
    compact_instruction: str = (
        "Create exactly one page using supplied character context; preserve profile, relationships, "
        "arc, appearance, and dialogue voice constraints."
    )
    reused_context_keys: tuple[str, ...] = ()
    duplicate_context_elided: bool = True
    prompt_generated: Literal[False] = False


class CharacterConsistencySummary(DirectorModel):
    """Boundary summary for the Character Consistency Standard."""

    project_id: str
    page_reference: str
    standard_stages: tuple[str, ...] = (
        "registry_projection",
        "profile_validation",
        "relationship_validation",
        "arc_validation",
        "appearance_validation",
        "dialogue_voice_validation",
    )
    character_changed: Literal[False] = False
    relationship_changed: Literal[False] = False
    appearance_changed: Literal[False] = False
    dialogue_changed: Literal[False] = False
    automatic_action_taken: Literal[False] = False
    findings: tuple[str, ...] = ()


class CharacterEngineReport(DirectorModel):
    """Transport-neutral Character Engine v1 report for one immutable context."""

    registry: CharacterRegistryDTO
    profile: CharacterProfileDTO
    relationships: RelationshipGraphDTO
    arc: CharacterArcManagerDTO
    appearance: AppearanceConsistencyDTO
    dialogue_voice: DialogueVoiceProfileDTO
    prompt_brief: CharacterPromptBriefDTO
    summary: CharacterConsistencySummary
    analysis_only: Literal[True] = True


class V56CharacterEngineService:
    """Build one-page character-consistency reports from supplied evidence."""

    def character_engine(self, project_id: str, context: WorkflowContext) -> CharacterEngineReport:
        page_reference = _page_reference(context)
        character_value = _context_value(context, "character_context")
        story_value = _context_value(context, "story_context")
        world_value = _context_value(context, "world_context")
        timeline_value = _context_value(context, "timeline_context")
        registry_value = _context_value(context, "character_registry")
        character_data = _mapping(character_value)
        registry_data = _mapping(registry_value)
        appearance_data = _mapping(character_data.get("appearance"))
        voice_data = _mapping(character_data.get("voice"))
        arc_data = _mapping(character_data.get("arc"))

        active_character_id = _optional_text(character_data.get("id"))
        if active_character_id is None and character_data:
            active_character_id = "current-character"
        registry_ids = _registry_ids(registry_data, active_character_id)
        registry_evidence_available = bool(registry_data)
        name_available = bool(character_data.get("name"))
        motivation_available = bool(
            character_data.get("motivation") or context.metadata.get("character_motivation")
        )
        story_available = bool(story_value)
        world_available = bool(world_value)
        timeline_available = bool(timeline_value)
        profile_valid = name_available and motivation_available and story_available and world_available
        relationship_edges = _relationship_edges(character_data, active_character_id)
        relationships_valid = bool(relationship_edges) and all(
            target in registry_ids for _, target, _ in relationship_edges
        )
        arc_goal_available = bool(arc_data.get("goal"))
        arc_stage_available = bool(arc_data.get("stage"))
        arc_valid = arc_goal_available and arc_stage_available and timeline_available
        hair_available = bool(appearance_data.get("hair"))
        eyes_available = bool(appearance_data.get("eyes"))
        clothing_available = bool(appearance_data.get("clothing"))
        accessories_available = bool(appearance_data.get("accessories"))
        appearance_valid = (
            hair_available and eyes_available and clothing_available and accessories_available
        )
        style_available = bool(voice_data.get("style"))
        markers = _string_references(voice_data.get("markers"))
        voice_valid = style_available and bool(markers)
        findings = _findings(
            name_available=name_available,
            motivation_available=motivation_available,
            story_available=story_available,
            world_available=world_available,
            registry_ids=registry_ids,
            registry_evidence_available=registry_evidence_available,
            relationship_edges=relationship_edges,
            relationships_valid=relationships_valid,
            arc_goal_available=arc_goal_available,
            arc_stage_available=arc_stage_available,
            timeline_available=timeline_available,
            appearance_valid=appearance_valid,
            style_available=style_available,
            markers=markers,
        )

        return CharacterEngineReport(
            registry=CharacterRegistryDTO(
                project_id=project_id,
                page_reference=page_reference,
                character_ids=registry_ids,
                active_character_id=active_character_id,
                registry_evidence_available=registry_evidence_available,
            ),
            profile=CharacterProfileDTO(
                character_id=active_character_id,
                name_available=name_available,
                motivation_available=motivation_available,
                story_context_available=story_available,
                world_context_available=world_available,
                profile_valid=profile_valid,
                status=_status(profile_valid),
            ),
            relationships=RelationshipGraphDTO(
                nodes=registry_ids,
                edges=relationship_edges,
                relationships_valid=relationships_valid,
                status=_status(relationships_valid),
            ),
            arc=CharacterArcManagerDTO(
                goal_available=arc_goal_available,
                stage_available=arc_stage_available,
                timeline_context_available=timeline_available,
                arc_valid=arc_valid,
                status=_status(arc_valid),
            ),
            appearance=AppearanceConsistencyDTO(
                hair_available=hair_available,
                eyes_available=eyes_available,
                clothing_available=clothing_available,
                accessories_available=accessories_available,
                appearance_valid=appearance_valid,
                status=_status(appearance_valid),
            ),
            dialogue_voice=DialogueVoiceProfileDTO(
                style_available=style_available,
                marker_count=len(markers),
                voice_valid=voice_valid,
                status=_status(voice_valid),
            ),
            prompt_brief=CharacterPromptBriefDTO(
                page_reference=page_reference,
                reused_context_keys=tuple(
                    key
                    for key, value in (
                        ("character_context", character_value),
                        ("character_registry", registry_value),
                        ("story_context", story_value),
                        ("world_context", world_value),
                        ("timeline_context", timeline_value),
                    )
                    if value
                ),
            ),
            summary=CharacterConsistencySummary(
                project_id=project_id,
                page_reference=page_reference,
                findings=findings,
            ),
        )


def _context_value(context: WorkflowContext, key: str) -> object:
    return context.metadata.get(key) or context.page.get(key)


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _registry_ids(registry: Mapping[str, object], active_character_id: str | None) -> tuple[str, ...]:
    identifiers = tuple(str(identifier) for identifier in registry if str(identifier))
    if active_character_id is not None and active_character_id not in identifiers:
        return (*identifiers, active_character_id)
    return identifiers


def _relationship_edges(
    character: Mapping[str, object], active_character_id: str | None
) -> tuple[tuple[str, str, str], ...]:
    if active_character_id is None:
        return ()
    relationships = character.get("relationships")
    if not isinstance(relationships, Sequence) or isinstance(relationships, str | bytes):
        return ()
    edges: list[tuple[str, str, str]] = []
    for relationship in relationships:
        relation = _mapping(relationship)
        target = _optional_text(relation.get("target"))
        relationship_type = _optional_text(relation.get("type"))
        if target is not None and relationship_type is not None:
            edges.append((active_character_id, target, relationship_type))
    return tuple(edges)


def _string_references(value: object) -> tuple[str, ...]:
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return tuple(str(item) for item in value if str(item))
    return ()


def _page_reference(context: WorkflowContext) -> str:
    value = context.page.get("id")
    return str(value) if value is not None else "current-page"


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _status(valid: bool) -> EvidenceStatus:
    return "ready" if valid else "needs_evidence"


def _findings(
    *,
    name_available: bool,
    motivation_available: bool,
    story_available: bool,
    world_available: bool,
    registry_ids: tuple[str, ...],
    registry_evidence_available: bool,
    relationship_edges: tuple[tuple[str, str, str], ...],
    relationships_valid: bool,
    arc_goal_available: bool,
    arc_stage_available: bool,
    timeline_available: bool,
    appearance_valid: bool,
    style_available: bool,
    markers: tuple[str, ...],
) -> tuple[str, ...]:
    findings: list[str] = []
    for name, available in (
        ("character name", name_available),
        ("character motivation", motivation_available),
        ("story_context", story_available),
        ("world_context", world_available),
        ("character arc goal", arc_goal_available),
        ("character arc stage", arc_stage_available),
        ("timeline_context", timeline_available),
        ("appearance profile", appearance_valid),
        ("dialogue voice style", style_available),
        ("dialogue voice markers", bool(markers)),
    ):
        if not available:
            findings.append(f"Missing {name} evidence.")
    if not registry_evidence_available:
        findings.append("Missing character registry evidence.")
    if not relationship_edges:
        findings.append("Missing character relationship evidence.")
    elif not relationships_valid:
        findings.append("Each character relationship target must exist in the supplied registry.")
    return tuple(findings)
