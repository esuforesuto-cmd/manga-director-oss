"""Measure v5 One Creative Platform report composition without operations."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.platform import (
    UnifiedContextReferenceDTO,
    UnifiedPlatformMaturityService,
)
from manga_director.workflow import WorkflowContext


def main() -> None:
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.PROMPT_BUILT)
    references = (
        UnifiedContextReferenceDTO(
            domain="workspace",
            context_id="workspace-1",
            source_module="workspace",
            source_reference="workspace:workspace-1",
        ),
        UnifiedContextReferenceDTO(
            domain="knowledge",
            context_id="knowledge-1",
            source_module="knowledge",
            source_reference="knowledge:knowledge-1",
        ),
        UnifiedContextReferenceDTO(
            domain="agent",
            context_id="agent-1",
            source_module="agents",
            source_reference="agent:agent-1",
        ),
        UnifiedContextReferenceDTO(
            domain="production",
            context_id="production-1",
            source_module="production",
            source_reference="production:production-1",
        ),
    )
    service = UnifiedPlatformMaturityService()
    elapsed = timeit(lambda: service.report("project", context, references), number=1_000)
    print(f"unified-platform-v5 projections: {elapsed:.6f}s")


if __name__ == "__main__":
    main()

