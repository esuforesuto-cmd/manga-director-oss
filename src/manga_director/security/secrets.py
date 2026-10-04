"""Secret retrieval boundary backed by environment variables and an optional .env file."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from manga_director.domain.exceptions import ConfigurationError


class SecretManager(Protocol):
    """Retrieve a named secret without persisting it in project configuration."""

    def get(self, name: str, *, required: bool = True) -> str | None:
        """Return a secret or raise when a required secret is unavailable."""


@dataclass(frozen=True, slots=True)
class CredentialReference:
    """A secret-safe credential configuration projection."""

    name: str
    required: bool
    configured: bool


class CredentialManager:
    """Validate and resolve credentials through an injected secret boundary."""

    _credential_name = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")

    def __init__(self, secret_manager: SecretManager) -> None:
        self.secret_manager = secret_manager

    def get(self, name: str, *, required: bool = True) -> str | None:
        """Resolve one validated credential without persisting or logging its value."""
        self._validate_name(name)
        return self.secret_manager.get(name, required=required)

    def reference(self, name: str, *, required: bool = True) -> CredentialReference:
        """Return configuration status without exposing the credential value."""
        self._validate_name(name)
        return CredentialReference(
            name=name,
            required=required,
            configured=bool(self.secret_manager.get(name, required=False)),
        )

    def _validate_name(self, name: str) -> None:
        if not self._credential_name.fullmatch(name):
            raise ConfigurationError("Credential names must be uppercase environment variable names.")


class EnvironmentSecretManager:
    """Read secrets from the process environment, optionally supplemented by .env."""

    def __init__(self, dotenv: Path | None = None) -> None:
        self._values = dict(os.environ)
        if dotenv is None or not dotenv.exists():
            return
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            if "=" not in line or line.lstrip().startswith("#"):
                continue
            key, value = line.split("=", 1)
            self._values.setdefault(key.strip(), value.strip())

    def get(self, name: str, *, required: bool = True) -> str | None:
        value = self._values.get(name)
        if required and not value:
            raise ConfigurationError(f"Required secret '{name}' is not configured.")
        return value
