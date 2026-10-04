"""Authentication and authorization boundaries for application adapters."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from hmac import compare_digest
from typing import Protocol


class AuthenticationProvider(Protocol):
    """Resolve a principal from optional client credentials."""

    def authenticate(self, credentials: object | None = None) -> str | None:
        """Return an authenticated principal, if any."""


class AuthorizationPolicy(Protocol):
    """Decide whether a principal may perform an action on a resource."""

    def allows(
        self,
        principal: str | None,
        action: str,
        resource: str | None = None,
    ) -> bool:
        """Return whether the requested action is allowed."""


class NoAuthProvider:
    """Development-only provider that exposes an anonymous principal."""

    def authenticate(self, credentials: object | None = None) -> str | None:
        del credentials
        return "anonymous"


class AllowAllPolicy:
    """Development-only policy that permits every action."""

    def allows(
        self,
        principal: str | None,
        action: str,
        resource: str | None = None,
    ) -> bool:
        del principal, action, resource
        return True


class StaticTokenAuthenticationProvider:
    """Authenticate caller-supplied static tokens without retaining credentials externally."""

    def __init__(self, tokens: Mapping[str, str]) -> None:
        credentials = tuple(tokens.items())
        if any(not token or not principal for token, principal in credentials):
            raise ValueError("Token credentials must contain non-empty tokens and principals.")
        self._credentials = credentials

    def authenticate(self, credentials: object | None = None) -> str | None:
        if not isinstance(credentials, str):
            return None
        for token, principal in self._credentials:
            if compare_digest(credentials, token):
                return principal
        return None


class RoleAuthorizationPolicy:
    """Authorize exact actions from caller-supplied principal role assignments."""

    def __init__(
        self,
        roles_by_principal: Mapping[str, Iterable[str]],
        actions_by_role: Mapping[str, Iterable[str]],
    ) -> None:
        self._roles_by_principal = {
            principal: frozenset(roles) for principal, roles in roles_by_principal.items()
        }
        self._actions_by_role = {
            role: frozenset(actions) for role, actions in actions_by_role.items()
        }

    def allows(
        self,
        principal: str | None,
        action: str,
        resource: str | None = None,
    ) -> bool:
        del resource
        if principal is None or not action:
            return False
        return any(
            action in self._actions_by_role.get(role, frozenset())
            for role in self._roles_by_principal.get(principal, frozenset())
        )
