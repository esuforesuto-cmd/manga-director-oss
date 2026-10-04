import pytest

from manga_director.domain.exceptions import ValidationError
from manga_director.security import (
    AuditLogger,
    MemoryRateLimiter,
    SecurityFramework,
)


class _AuthenticationProvider:
    def authenticate(self, credentials: object | None = None) -> str | None:
        assert credentials == "token"
        return "editor-1"


class _AuthorizationPolicy:
    def allows(self, principal: str | None, action: str, resource: str | None = None) -> bool:
        return principal == "editor-1" and action == "review" and resource == "page-1"


def test_security_framework_authenticates_authorizes_and_audits() -> None:
    audit = AuditLogger()
    framework = SecurityFramework(
        authentication_provider=_AuthenticationProvider(),
        authorization_policy=_AuthorizationPolicy(),
        audit_logger=audit,
    )

    decision = framework.authorize(
        "review",
        credentials="token",
        resource="page-1",
        project_id="project-1",
    )

    assert decision.allowed is True
    assert decision.principal == "editor-1"
    assert decision.rate_limited is False
    assert audit.entries[0]["action"] == "security.authorization"
    assert audit.entries[0]["metadata"]["allowed"] is True


def test_security_framework_denies_without_a_policy_and_records_the_decision() -> None:
    framework = SecurityFramework()

    decision = framework.authorize("review", resource="page-1")

    assert decision.allowed is False
    assert decision.audit_recorded is True
    assert framework.audit_logger.entries[0]["metadata"]["allowed"] is False


def test_security_framework_rate_limits_before_authorization() -> None:
    framework = SecurityFramework(
        authentication_provider=_AuthenticationProvider(),
        authorization_policy=_AuthorizationPolicy(),
        rate_limiter=MemoryRateLimiter(limit=1),
    )

    assert framework.authorize("review", credentials="token", resource="page-1").allowed is True
    decision = framework.authorize("review", credentials="token", resource="page-1")

    assert decision.allowed is False
    assert decision.rate_limited is True


def test_security_framework_rejects_an_empty_action() -> None:
    with pytest.raises(ValidationError, match="must not be empty"):
        SecurityFramework().authorize("   ")


def test_security_framework_reuses_identifier_validation() -> None:
    framework = SecurityFramework()

    assert framework.validate_identifier("project_1") == "project_1"
    with pytest.raises(ValidationError):
        framework.validate_identifier("../project")
