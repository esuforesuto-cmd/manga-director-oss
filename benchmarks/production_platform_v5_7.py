"""Measure the read-only v5.7 Production Platform report for one approved page."""

from timeit import timeit

from manga_director.domain.events import EventType, WorkflowEvent
from manga_director.domain.state_machine import PageState
from manga_director.production import (
    PluginLifecycleDescriptorDTO,
    ProductionTemplateDTO,
    V57ProductionOrchestrator,
)
from manga_director.workflow import WorkflowContext


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "benchmark-page"},
        state=PageState.APPROVED,
        artifacts={
            PageState.STORYBOARDED.value: {"panels": []},
            PageState.GENERATED.value: {"image": "benchmark.png"},
            PageState.QUALITY_CHECKED.value: {"status": "passed"},
        },
        metadata={
            "story_context": {"beat": "resolution"},
            "character_context": {"hero": "Aki"},
            "world_context": {"location": "station"},
            "timeline_context": {"scene": 8},
            "automation_templates": ["approved-export"],
            "automation_rules": ["human-review-boundary"],
            "workflow_history": [{"step": "approval"}],
            "print_export": {"trim_size": "A5", "dpi": 600},
            "web_export": {"format": "png", "width": 1600},
            "ebook_export": {"format": "epub", "reading_direction": "rtl"},
            "publishing_metadata": {"title": "Benchmark", "language": "ja", "rights": "creator"},
        },
        events=[WorkflowEvent(event_type=EventType.PAGE_APPROVED)],
    )


def main() -> None:
    context = _context()
    service = V57ProductionOrchestrator()
    template = ProductionTemplateDTO(
        template_id="approved-export",
        page_reference="benchmark-page",
        required_evidence=("Storyboarded", "QualityChecked"),
    )
    plugin = PluginLifecycleDescriptorDTO(
        plugin_name="layout-tools", version="1.0", enabled=True, active=True
    )
    elapsed = timeit(
        lambda: service.production_platform("benchmark", context, templates=(template,), plugins=(plugin,)),
        number=500,
    )
    print(f"production-platform-v5.7 projections: {elapsed:.6f}s")


if __name__ == "__main__":
    main()
