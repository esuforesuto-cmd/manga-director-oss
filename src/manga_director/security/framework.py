"""Composable security boundary for adapter-facing authorization decisions."""

from __future__ import annotations

from dataclasses import dataclass

from manga_director.domain.exceptions import ValidationError
from manga_director.security.audit import AuditLogger
from manga_director.security.auth import AuthenticationProvider, AuthorizationPolicy
from manga_director.security.rate_limit import RateLimiter
from manga_director.security.validation import SecurityValidator


@dataclass(frozen=True, slots=True)
class SecurityDecision:
    """An auditable authorization decision without workflow side effects."""

    principal: str | None
    action: str
    resource: str | None
    allowed: bool
    rate_limited: bool
    audit_recorded: bool


class SecurityFramework:
    """Compose existing security boundaries with deny-by-default authorization."""

    def __init__(
        self,
        *,
        authentication_provider: AuthenticationProvider | None = None,
        authorization_policy: AuthorizationPolicy | None = None,
        rate_limiter: RateLimiter | None = None,
        validator: SecurityValidator | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.authentication_provider = authentication_provider
        self.authorization_policy = authorization_policy
        self.rate_limiter = rate_limiter
        self.validator = validator or SecurityValidator()
        self.audit_logger = audit_logger or AuditLogger()

    def authorize(
        self,
        action: str,
        *,
        credentials: object | None = None,
        resource: str | None = None,
        rate_limit_key: str | None = None,
        project_id: str | None = None,
    ) -> SecurityDecision:
        """Authenticate, rate-limit, authorize, and record one boundary decision."""
        if not action.strip():
            raise ValidationError("Security action must not be empty.")

        principal = (
            self.authentication_provider.authenticate(credentials)
            if self.authentication_provider is not None
            else None
        )
        limiter_key = rate_limit_key or principal or "anonymous"
        rate_allowed = self.rate_limiter is None or self.rate_limiter.allow(limiter_key)
        policy_allowed = (
            rate_allowed
            and self.authorization_policy is not None
            and self.authorization_policy.allows(principal, action, resource)
        )
        decision = SecurityDecision(
            principal=principal,
            action=action,
            resource=resource,
            allowed=policy_allowed,
            rate_limited=not rate_allowed,
            audit_recorded=True,
        )
        self.audit_logger.record(
            "security.authorization",
            project_id=project_id,
            actor=principal,
            metadata={
                "action": action,
                "resource": resource,
                "allowed": decision.allowed,
                "rate_limited": decision.rate_limited,
            },
        )
        return decision

    def validate_identifier(self, value: str, label: str = "identifier") -> str:
        """Delegate identifier validation to the configured security validator."""
        return self.validator.identifier(value, label)
