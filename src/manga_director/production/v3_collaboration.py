"""v3 advisory Multi-Agent, Creative Knowledge, Director Intelligence, and Review DTOs.

The module is deliberately planning-only.  It projects existing v3 Foundation
reports into collaboration and review evidence without executing Agents,
mutating repositories, invoking providers, or altering a workflow.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.production.v3_foundation import (
    DirectorPlanningService,
    KnowledgeReference,
)
from manga_director.workflow.contracts import WorkflowContext


class AgentProfile(DirectorModel):
    """A proposed collaboration role, not an instantiated runtime Agent."""

    name: str
    role: str
    review_required: bool = True
    execution_enabled: bool = False


class AgentCapability(DirectorModel):
    name: str
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    advisory_only: bool = True


class AgentAssignment(DirectorModel):
    agent: AgentProfile
    capability: AgentCapability
    objective: str
    dependencies: tuple[str, ...] = ()
    human_checkpoint: str = "human review"
    assigned_for_execution: bool = False


class AgentCollaborationPlan(DirectorModel):
    page_reference: str
    current_state: PageState
    assignments: tuple[AgentAssignment, ...] = ()
    dependency_edges: tuple[tuple[str, str], ...] = ()
    execution_dispatched: bool = False


class CollaborationSummary(DirectorModel):
    participant_count: int = Field(ge=0)
    checkpoint_count: int = Field(ge=0)
    next_command: str | None = None
    messages: tuple[str, ...] = ()
    automatic_action_taken: bool = False


class AgentCoordinationReport(DirectorModel):
    plan: AgentCollaborationPlan
    summary: CollaborationSummary
    coordination_only: bool = True


class KnowledgeTopic(DirectorModel):
    topic: str
    references: tuple[str, ...] = ()
    source: Literal["repository_projection"] = "repository_projection"
    persistence_mutated: bool = False


class CharacterKnowledge(KnowledgeTopic):
    topic: Literal["character"] = "character"


class WorldKnowledge(KnowledgeTopic):
    topic: Literal["world"] = "world"


class StoryKnowledge(KnowledgeTopic):
    topic: Literal["story"] = "story"


class SceneKnowledge(KnowledgeTopic):
    topic: Literal["scene"] = "scene"


class AssetKnowledge(KnowledgeTopic):
    topic: Literal["asset"] = "asset"


class KnowledgeRelationshipReport(DirectorModel):
    nodes: tuple[str, ...] = ()
    edges: tuple[tuple[str, str], ...] = ()
    relationship_count: int = Field(ge=0)
    analysis_only: bool = True


class CreativeKnowledgeReport(DirectorModel):
    character: CharacterKnowledge
    world: WorldKnowledge
    story: StoryKnowledge
    scene: SceneKnowledge
    asset: AssetKnowledge
    relationships: KnowledgeRelationshipReport
    repository_read_only: bool = True


class CreativeDecisionAnalysis(DirectorModel):
    purpose: str
    reader_effect: str
    next_command: str | None = None
    decision_only: bool = True


class PlanningComparison(DirectorModel):
    baseline: str
    alternative: str
    comparison: str
    selected_automatically: bool = False


class AlternativePlanningReport(DirectorModel):
    alternatives: tuple[str, ...] = ()
    comparison: PlanningComparison
    execution_enabled: bool = False


class CreativeRiskAnalysis(DirectorModel):
    level: Literal["low", "medium"]
    factors: tuple[str, ...] = ()
    mitigation: str
    automatic_mitigation: bool = False


class CreativeRecommendation(DirectorModel):
    message: str
    requires_human_review: bool = True
    execution_enabled: bool = False


class DirectorIntelligenceSummary(DirectorModel):
    decision: CreativeDecisionAnalysis
    alternatives: AlternativePlanningReport
    risk: CreativeRiskAnalysis
    recommendation: CreativeRecommendation
    workflow_modified: bool = False


class StoryReview(DirectorModel):
    focus: tuple[str, ...] = ("purpose", "reader effect", "hook")
    findings: tuple[str, ...] = ()
    review_only: bool = True


class StoryboardReview(DirectorModel):
    storyboard_persisted: bool
    findings: tuple[str, ...] = ()
    review_only: bool = True


class CharacterConsistencyReview(DirectorModel):
    references_checked: int = Field(ge=0)
    findings: tuple[str, ...] = ()
    review_only: bool = True


class KnowledgeConsistencyReview(DirectorModel):
    relationship_count: int = Field(ge=0)
    findings: tuple[str, ...] = ()
    review_only: bool = True


class CreativeQualityReport(DirectorModel):
    criteria: tuple[str, ...] = ("clarity", "continuity", "storyboard evidence")
    warnings: tuple[str, ...] = ()
    quality_passed: bool = False
    approval_granted: bool = False


class ReviewSummary(DirectorModel):
    findings: tuple[str, ...] = ()
    recommended_next_command: str | None = None
    review_performed: bool = False
    automatic_action_taken: bool = False


class ReviewPipelineReport(DirectorModel):
    story: StoryReview
    storyboard: StoryboardReview
    character_consistency: CharacterConsistencyReview
    knowledge_consistency: KnowledgeConsistencyReview
    quality: CreativeQualityReport
    summary: ReviewSummary
    diagnostics_only: bool = True


class AgentDashboardDTO(DirectorModel):
    report: AgentCoordinationReport
    automatic_action_taken: bool = False


class CreativeKnowledgeDTO(DirectorModel):
    report: CreativeKnowledgeReport
    automatic_action_taken: bool = False


class DirectorIntelligenceDTO(DirectorModel):
    report: DirectorIntelligenceSummary
    automatic_action_taken: bool = False


class ReviewPipelineDTO(DirectorModel):
    report: ReviewPipelineReport
    automatic_action_taken: bool = False


class CollaborationPlanningService:
    """Build v3 Iteration 2 advisory reports from the v3 Foundation service."""

    def __init__(self, foundation: DirectorPlanningService) -> None:
        self._foundation = foundation

    def multi_agent_foundation(self, context: WorkflowContext) -> AgentCoordinationReport:
        session = self._foundation.director_session(context)
        profiles = _profiles()
        assignments = tuple(
            AgentAssignment(
                agent=profile,
                capability=_capability(profile.name),
                objective=_objective(profile.name, session.session.creative_goal.purpose),
                dependencies=("editor",) if profile.name != "editor" else (),
            )
            for profile in profiles
        )
        names = tuple(profile.name for profile in profiles)
        edges = tuple((names[index], names[index + 1]) for index in range(len(names) - 1))
        return AgentCoordinationReport(
            plan=AgentCollaborationPlan(
                page_reference=session.session.planning_context.page_reference,
                current_state=context.state,
                assignments=assignments,
                dependency_edges=edges,
            ),
            summary=CollaborationSummary(
                participant_count=len(assignments),
                checkpoint_count=len(assignments),
                next_command=session.summary.recommended_command,
                messages=("Collaboration is a proposed review plan; no Agent was executed.",),
            ),
        )

    def creative_knowledge(self, context: WorkflowContext | None = None) -> CreativeKnowledgeReport:
        snapshot = self._foundation.knowledge_foundation().snapshot
        tags = tuple(tag.value for reference in snapshot.references for tag in reference.tags)
        character, world, story, scene, asset = _topics(tags, context)
        relationships = _relationships(snapshot.references)
        return CreativeKnowledgeReport(
            character=character,
            world=world,
            story=story,
            scene=scene,
            asset=asset,
            relationships=relationships,
        )

    def director_intelligence(self, context: WorkflowContext) -> DirectorIntelligenceSummary:
        session = self._foundation.director_session(context)
        creative = self._foundation.creative_planning(context)
        risk_factors = () if creative.panels.storyboard_persisted else ("Storyboard evidence is not persisted.",)
        risk = CreativeRiskAnalysis(
            level="medium" if risk_factors else "low",
            factors=risk_factors,
            mitigation="Use the existing StateMachine next step after human review.",
        )
        return DirectorIntelligenceSummary(
            decision=CreativeDecisionAnalysis(
                purpose=session.session.creative_goal.purpose,
                reader_effect=session.session.creative_goal.reader_effect,
                next_command=session.summary.recommended_command,
            ),
            alternatives=AlternativePlanningReport(
                alternatives=("state_machine_next_step", "human_review"),
                comparison=PlanningComparison(
                    baseline="state_machine_next_step",
                    alternative="human_review",
                    comparison="Both options are advisory; only a human may choose an existing workflow command.",
                ),
            ),
            risk=risk,
            recommendation=CreativeRecommendation(
                message="Review creative intent and evidence before explicitly executing the legal next step."
            ),
        )

    def review_pipeline(self, context: WorkflowContext) -> ReviewPipelineReport:
        creative = self._foundation.creative_planning(context)
        knowledge = self.creative_knowledge(context)
        intelligence = self._foundation.workflow_intelligence(context)
        storyboard_finding = () if creative.panels.storyboard_persisted else ("Storyboard evidence is missing.",)
        warnings = storyboard_finding or (
            "Review remains diagnostic; existing QualityReview and HumanApproval are still required.",
        )
        return ReviewPipelineReport(
            story=StoryReview(findings=(f"Purpose: {creative.page.purpose}",)),
            storyboard=StoryboardReview(
                storyboard_persisted=creative.panels.storyboard_persisted,
                findings=storyboard_finding,
            ),
            character_consistency=CharacterConsistencyReview(
                references_checked=len(knowledge.character.references)
            ),
            knowledge_consistency=KnowledgeConsistencyReview(
                relationship_count=knowledge.relationships.relationship_count
            ),
            quality=CreativeQualityReport(warnings=warnings),
            summary=ReviewSummary(
                findings=warnings,
                recommended_next_command=intelligence.recommendation.command,
            ),
        )

    def agent_dashboard(self, context: WorkflowContext) -> AgentDashboardDTO:
        return AgentDashboardDTO(report=self.multi_agent_foundation(context))

    def creative_knowledge_dashboard(self, context: WorkflowContext | None = None) -> CreativeKnowledgeDTO:
        return CreativeKnowledgeDTO(report=self.creative_knowledge(context))

    def director_intelligence_dashboard(self, context: WorkflowContext) -> DirectorIntelligenceDTO:
        return DirectorIntelligenceDTO(report=self.director_intelligence(context))

    def review_pipeline_dashboard(self, context: WorkflowContext) -> ReviewPipelineDTO:
        return ReviewPipelineDTO(report=self.review_pipeline(context))


def _profiles() -> tuple[AgentProfile, ...]:
    return (
        AgentProfile(name="editor", role="editorial review"),
        AgentProfile(name="story", role="story planning"),
        AgentProfile(name="character", role="character continuity"),
        AgentProfile(name="storyboard", role="panel planning"),
        AgentProfile(name="review", role="quality and consistency review"),
    )


def _capability(name: str) -> AgentCapability:
    return AgentCapability(
        name=f"{name}_advisory",
        inputs=("one_page_context", "repository_projection"),
        outputs=("reviewable_dto",),
    )


def _objective(name: str, purpose: str) -> str:
    return f"{name} advisory review for: {purpose}"


def _topics(
    tags: tuple[str, ...], context: WorkflowContext | None
) -> tuple[CharacterKnowledge, WorldKnowledge, StoryKnowledge, SceneKnowledge, AssetKnowledge]:
    scene = (str(context.page.get("id", "page")),) if context is not None else ()
    return (
        CharacterKnowledge(references=_matching(tags, ("character", "cast"))),
        WorldKnowledge(references=_matching(tags, ("world", "location", "time"))),
        StoryKnowledge(references=_matching(tags, ("story", "theme", "plot"))),
        SceneKnowledge(references=scene + _matching(tags, ("scene", "chapter"))),
        AssetKnowledge(references=_matching(tags, ("asset", "image", "prompt"))),
    )


def _matching(tags: tuple[str, ...], prefixes: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(tag for tag in tags if tag.lower().startswith(prefixes))


def _relationships(references: tuple[KnowledgeReference, ...]) -> KnowledgeRelationshipReport:
    edges = tuple(
        (reference.identifier, tag.value) for reference in references for tag in reference.tags
    )
    nodes = tuple(reference.identifier for reference in references) + tuple(
        tag for _, tag in edges
    )
    return KnowledgeRelationshipReport(nodes=nodes, edges=edges, relationship_count=len(edges))
