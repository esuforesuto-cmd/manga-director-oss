import pytest

from manga_director.security import (
    RoleAuthorizationPolicy,
    SecurityFramework,
    StaticTokenAuthenticationProvider,
)


def test_static_token_authentication_returns_only_the_configured_principal() -> None:
    provider = StaticTokenAuthenticationProvider({"editor-token": "editor-1"})

    assert provider.authenticate("editor-token") == "editor-1"
    assert provider.authenticate("invalid-token") is None
    assert provider.authenticate(1) is None


def test_static_token_authentication_rejects_empty_configuration() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        StaticTokenAuthenticationProvider({"": "editor-1"})


def test_role_authorization_requires_an_assigned_role_and_exact_permission() -> None:
    policy = RoleAuthorizationPolicy(
        {"editor-1": {"editor"}, "artist-1": {"artist"}},
        {"editor": {"review", "approve"}, "artist": {"draw"}},
    )

    assert policy.allows("editor-1", "review") is True
    assert policy.allows("editor-1", "draw") is False
    assert policy.allows("unknown", "review") is False
    assert policy.allows(None, "review") is False


def test_security_framework_composes_static_authentication_and_role_authorization() -> None:
    framework = SecurityFramework(
        authentication_provider=StaticTokenAuthenticationProvider({"editor-token": "editor-1"}),
        authorization_policy=RoleAuthorizationPolicy(
            {"editor-1": {"editor"}}, {"editor": {"review"}}
        ),
    )

    allowed = framework.authorize("review", credentials="editor-token", resource="page-1")
    denied = framework.authorize("approve", credentials="editor-token", resource="page-1")

    assert allowed.allowed is True
    assert denied.allowed is False
