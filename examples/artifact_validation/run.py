"""Verify local release artifacts without building or uploading them."""

from pathlib import Path

from manga_director.cli.config import AppConfig
from manga_director.production import QualityAutomation, ReleaseReadiness, RepositoryMaintenance
from manga_director.repositories import InMemoryRepository


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    repository = InMemoryRepository()
    service = ReleaseReadiness(
        quality=QualityAutomation(repository=repository, configuration=AppConfig(), root=root),
        maintenance=RepositoryMaintenance(repository),
        root=root,
    )
    print(service.artifact_verification().to_json())


if __name__ == "__main__":
    main()
