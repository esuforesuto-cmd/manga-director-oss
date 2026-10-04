"""Render static package, SBOM, and release-asset validation evidence."""

from pathlib import Path

from manga_director.cli.config import AppConfig
from manga_director.production import QualityAutomation
from manga_director.repositories import InMemoryRepository


def main() -> None:
    quality = QualityAutomation(
        repository=InMemoryRepository(),
        configuration=AppConfig(),
        root=Path(__file__).resolve().parents[2],
    )
    print(quality.release_artifact_validation().to_markdown())


if __name__ == "__main__":
    main()
