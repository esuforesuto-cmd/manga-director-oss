import pytest

from manga_director.domain.exceptions import ValidationError
from manga_director.security import (
    AllowAllPolicy,
    AuditLogger,
    MemoryRateLimiter,
    NoAuthProvider,
    SecurityValidator,
    sanitize_output,
)


def test_auth_policy_and_rate_limit() -> None:
    assert NoAuthProvider().authenticate() == "anonymous"
    assert AllowAllPolicy().allows(None, "run")
    limiter = MemoryRateLimiter(limit=1)
    assert limiter.allow("client")
    assert not limiter.allow("client")


def test_validation_sanitization_and_audit() -> None:
    validator = SecurityValidator()
    assert validator.identifier("project_1") == "project_1"
    with pytest.raises(ValidationError):
        validator.identifier("../unsafe")
    assert "&lt;script&gt;" in sanitize_output("<script>")
    audit = AuditLogger()
    audit.record("workflow.execute", project_id="project_1")
    assert audit.entries[0]["action"] == "workflow.execute"
