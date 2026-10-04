"""Input validation and safe output rendering helpers."""

from __future__ import annotations

import html
import re
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from manga_director.domain.exceptions import ValidationError


class SecurityPolicy(BaseModel):
    """Configurable limits applied by the application boundary."""

    allowed_hosts: set[str] = Field(default_factory=set)
    allowed_file_extensions: set[str] = Field(
        default_factory=lambda: {".json", ".yaml", ".yml", ".md"}
    )
    max_upload_size: int = 10_000_000
    timeout: float = 10.0
    allowed_providers: set[str] = Field(default_factory=set)


class SecurityValidator:
    """Validate identifiers and external values before they reach application logic."""

    _identifier = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

    def __init__(self, policy: SecurityPolicy | None = None) -> None:
        self.policy = policy or SecurityPolicy()

    def identifier(self, value: str, label: str = "identifier") -> str:
        if not self._identifier.fullmatch(value):
            raise ValidationError(f"Invalid {label}.")
        return value

    def page_number(self, value: int) -> int:
        if value < 1:
            raise ValidationError("Page number must be positive.")
        return value

    def file_path(self, value: Path) -> Path:
        if value.suffix.lower() not in self.policy.allowed_file_extensions or ".." in value.parts:
            raise ValidationError("File path is not allowed.")
        return value

    def url(self, value: str) -> str:
        parsed = urlparse(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or (self.policy.allowed_hosts and parsed.hostname not in self.policy.allowed_hosts)
        ):
            raise ValidationError("URL is not allowed.")
        return value

    def metadata(self, value: dict[str, object]) -> dict[str, object]:
        if len(str(value)) > self.policy.max_upload_size:
            raise ValidationError("Metadata exceeds size limit.")
        return value


def sanitize_output(value: str) -> str:
    """Escape HTML and replace the local workspace path before presentation."""

    return html.escape(value, quote=True).replace(str(Path.cwd()), "[workspace]")
