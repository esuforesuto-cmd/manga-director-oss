"""Loader and packager for validated local SDK extensions."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from manga_director.domain.exceptions import ValidationError
from manga_director.sdk.context import ExtensionContext
from manga_director.sdk.extension import Extension
from manga_director.sdk.manifest import ExtensionValidator


class ExtensionLoader:
    """Load one local extension through its validated manifest entry point."""

    def __init__(self, validator: ExtensionValidator | None = None) -> None:
        self.validator = validator or ExtensionValidator()

    def load(self, manifest_path: Path, context: ExtensionContext) -> Extension:
        """Instantiate and initialize an extension declared by ``manifest_path``."""

        try:
            manifest = self.validator.load(manifest_path)
            module, attribute = manifest.entry_point.split(":", 1)
            extension = getattr(import_module(module), attribute)()
            if not isinstance(extension, Extension):
                raise TypeError("Entry point must produce an Extension")
            extension.initialize(context)
            return extension
        except (ImportError, AttributeError, TypeError, ValueError) as exc:
            raise ValidationError(f"Unable to load extension '{manifest_path}': {exc}") from exc

    @staticmethod
    def package(source: Path, destination: Path) -> Path:
        """Create a portable ZIP without changing its source directory."""

        required = [source / "manifest.yaml", source / "README.md", source / "LICENSE"]
        if not all(path.exists() for path in required) or not (source / "extension").is_dir():
            raise ValueError(
                "Extension package requires manifest.yaml, extension/, README.md, LICENSE"
            )
        with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
            for path in sorted(source.rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                    archive.write(path, path.relative_to(source))
        return destination
