"""Measure read-only v5.6 Manga Production OS projections for one approved page."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production import (
    V56CharacterEngineService,
    V56ExportEngineService,
    V56PageEngineService,
    V56ProductionPipelineService,
    V56ReviewEngineService,
    V56StoryEngineService,
)
from manga_director.workflow import WorkflowContext


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "benchmark-page"},
        state=PageState.APPROVED,
        artifacts={
            PageState.DESIGNED.value: {
                "purpose": "Reveal the ticket.",
                "reader_emotion": "anticipation",
                "hook": "Who sent it?",
                "big_moment": "The ticket is revealed.",
                "scene_transition": "Platform to train.",
                "panel_count": 1,
                "panel_roles": ["big moment"],
            },
            PageState.STORYBOARDED.value: {
                "panels": [
                    {
                        "number": 1,
                        "camera": "close-up",
                        "composition": "ticket draws the eye",
                        "background": "station platform",
                        "characters": ["aki"],
                        "dialogue": [],
                        "balloon_position": "upper right",
                    }
                ]
            },
            PageState.GENERATED.value: {"image_path": "benchmark.png"},
            PageState.QUALITY_CHECKED.value: {"passed": True},
        },
        metadata={
            "story_context": {"premise": "Aki seeks truth.", "chapter_goal": "Reveal ticket."},
            "character_context": {"id": "aki", "name": "Aki", "motivation": "Protect."},
            "world_context": {"location": "station"},
            "timeline_context": {"events": [{"sequence": 1}]},
            "print_export": {"trim_size": "B5", "dpi": 600},
            "web_export": {"format": "webp", "width": 1440},
            "ebook_export": {"format": "epub", "reading_direction": "rtl"},
            "publishing_metadata": {"title": "Benchmark", "language": "ja", "rights": "all"},
        },
    )


def main() -> None:
    context = _context()
    services = (
        V56ProductionPipelineService().production_pipeline,
        V56StoryEngineService().story_engine,
        V56CharacterEngineService().character_engine,
        V56PageEngineService().page_engine,
        V56ReviewEngineService().review_engine,
        V56ExportEngineService().export_engine,
    )
    elapsed = timeit(lambda: tuple(service("benchmark", context) for service in services), number=1_000)
    print(f"manga-production-os-v5.6 projections: {elapsed:.6f}s")


if __name__ == "__main__":
    main()
