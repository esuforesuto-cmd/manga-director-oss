"""Deterministic large-Project fixtures shared by v2.2 benchmark scenarios."""

from __future__ import annotations

from time import perf_counter

from manga_director.domain.project import Chapter, Page, Project


def make_large_project(page_count: int = 240, chapter_size: int = 24) -> Project:
    """Build a realistic-enough aggregate without generating any page artwork."""

    page_numbers = list(range(1, page_count + 1))
    chapters = [
        Chapter(
            id=f"chapter-{index // chapter_size + 1}",
            title=f"Chapter {index // chapter_size + 1}",
            page_numbers=page_numbers[index : index + chapter_size],
        )
        for index in range(0, page_count, chapter_size)
    ]
    pages = [
        Page(
            page_number=number,
            metadata={"scene": number // chapter_size, "character": "Aki"},
            history=[{"step": "Draft", "sequence": event} for event in range(4)],
        )
        for number in page_numbers
    ]
    return Project(id="large-project", title="Large Project", chapters=chapters, pages=pages)


def run() -> float:
    """Measure deterministic construction of a several-hundred-page aggregate."""

    started = perf_counter()
    make_large_project()
    return perf_counter() - started


if __name__ == "__main__":
    print(f"large_project: {run():.6f}s")
