"""Inspect image-backend metadata without calling image generation."""

from manga_director.adapters import ImageBackendRuntime
from manga_director.production import BackendManagement


def main() -> None:
    print(BackendManagement(ImageBackendRuntime()).inventory(refresh=True).to_markdown())


if __name__ == "__main__":
    main()
