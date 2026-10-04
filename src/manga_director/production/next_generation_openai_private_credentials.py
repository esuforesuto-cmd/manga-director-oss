"""Internal exact-key credential resolution for the OpenAI private transport.

The selector and resolved credential are provider-private runtime material.
They must never enter a DTO, report, evidence record, or public API.
"""

from __future__ import annotations

import os
from collections.abc import Callable

from manga_director.security import CredentialManager


class _CredentialResolutionFailure(Exception):
    """Private, intentionally detail-free resolution failure."""


class ExactKeySecretManager:
    """Resolve only the single selector privately bound at construction."""

    __slots__ = ("_lookup", "_selector")

    def __init__(
        self,
        selector: str,
        lookup: Callable[[str], str | None] | None = None,
    ) -> None:
        self._selector = selector
        self._lookup = lookup if lookup is not None else os.getenv

    def get(self, name: str, *, required: bool = True) -> str | None:
        """Look up one exact key without enumeration, fallback, or caching."""

        if name != self._selector:
            raise _CredentialResolutionFailure()
        try:
            value = self._lookup(name)
        except Exception:
            raise _CredentialResolutionFailure() from None
        if not isinstance(value, str) or not value.strip():
            if required:
                raise _CredentialResolutionFailure()
            return None
        return value


class OpenAIPrivateCredentialResolver:
    """Adapt one existing credential manager to the OpenAI private resolver port."""

    __slots__ = ("_credential_manager", "_selector")

    def __init__(self, credential_manager: CredentialManager, selector: str) -> None:
        self._credential_manager = credential_manager
        self._selector = selector

    def resolve(self) -> str:
        """Return one nonblank credential or raise a redacted private failure."""

        try:
            value = self._credential_manager.get(self._selector, required=True)
        except Exception:
            raise _CredentialResolutionFailure() from None
        if not isinstance(value, str) or not value.strip():
            raise _CredentialResolutionFailure()
        return value
