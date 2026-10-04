"""v5 unified platform and context foundations without ownership transfer.

These DTOs normalize caller-supplied references from existing platform modules.
They never load, merge, persist, authorize, or mutate their source contexts.
The domain StateMachine remains the only workflow transition authority.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.workflow.contracts import WorkflowContext


class UnifiedContextReferenceDTO(DirectorModel):
    """An explicit reference to an existing module-owned context."""

    domain: Literal["workspace", "knowledge", "agent", "production"]
    context_id: str
    source_module: str
    source_reference: str
    freshness: Literal["supplied", "unknown"] = "supplied"
    source_loaded: bool = False
    source_mutated: bool = False


class UnifiedCreativeContextDTO(DirectorModel):
    """Immutable one-Page correlation context for additive platform reports."""

    platform_id: str
    project_id: str
    page_reference: str
    workflow_state: str
    page_count: Literal[1] = 1
    references: tuple[UnifiedContextReferenceDTO, ...] = ()
    state_machine_authoritative: bool = True
    context_persisted: bool = False
    workflow_mutated: bool = False


class UnifiedPlatformModuleDTO(DirectorModel):
    module_id: str
    owner_layer: str
    context_supported: bool = True
    public_contract_preserved: bool = True
    source_of_truth_transferred: bool = False


class UnifiedPlatformSummary(DirectorModel):
    module_count: int = Field(default=0, ge=0)
    context_reference_count: int = Field(default=0, ge=0)
    aggregate_persisted: bool = False
    automatic_action_taken: bool = False


class UnifiedPlatformFoundationReport(DirectorModel):
    context: UnifiedCreativeContextDTO
    modules: tuple[UnifiedPlatformModuleDTO, ...]
    summary: UnifiedPlatformSummary
    planning_only: bool = True


class UnifiedCreativeContextFactory:
    """Builds a context from supplied references; it never reads their owners."""

    def create(
        self,
        project_id: str,
        workflow_context: WorkflowContext,
        references: tuple[UnifiedContextReferenceDTO, ...] = (),
    ) -> UnifiedCreativeContextDTO:
        domains = tuple(reference.domain for reference in references)
        if len(domains) != len(set(domains)):
            raise ValueError("only one reference per unified context domain is allowed")
        page_reference = _page_reference(workflow_context)
        return UnifiedCreativeContextDTO(
            platform_id=f"unified-platform:{project_id}:{page_reference}",
            project_id=project_id,
            page_reference=page_reference,
            workflow_state=workflow_context.state.value,
            references=references,
        )


class UnifiedPlatformFoundationService:
    """Composes static module metadata around an existing workflow context."""

    def __init__(self, context_factory: UnifiedCreativeContextFactory | None = None) -> None:
        self._context_factory = context_factory or UnifiedCreativeContextFactory()

    def report(
        self,
        project_id: str,
        workflow_context: WorkflowContext,
        references: tuple[UnifiedContextReferenceDTO, ...] = (),
    ) -> UnifiedPlatformFoundationReport:
        context = self._context_factory.create(project_id, workflow_context, references)
        modules = _platform_modules()
        return UnifiedPlatformFoundationReport(
            context=context,
            modules=modules,
            summary=UnifiedPlatformSummary(
                module_count=len(modules), context_reference_count=len(context.references)
            ),
        )


def _platform_modules() -> tuple[UnifiedPlatformModuleDTO, ...]:
    return (
        UnifiedPlatformModuleDTO(module_id="workspace", owner_layer="application"),
        UnifiedPlatformModuleDTO(module_id="knowledge", owner_layer="knowledge"),
        UnifiedPlatformModuleDTO(module_id="agent-platform", owner_layer="application"),
        UnifiedPlatformModuleDTO(module_id="production", owner_layer="application"),
        UnifiedPlatformModuleDTO(module_id="enterprise", owner_layer="application"),
        UnifiedPlatformModuleDTO(module_id="decision", owner_layer="application"),
        UnifiedPlatformModuleDTO(module_id="ecosystem", owner_layer="application"),
    )


def _page_reference(context: WorkflowContext) -> str:
    page_id = context.page.get("id")
    return str(page_id) if page_id is not None else "page"

