import pytest

from manga_director.domain.exceptions import ConfigurationError
from manga_director.security import CredentialManager


class _SecretManager:
    def __init__(self, values: dict[str, str]) -> None:
        self.values = values

    def get(self, name: str, *, required: bool = True) -> str | None:
        value = self.values.get(name)
        if required and not value:
            raise ConfigurationError(f"Required secret '{name}' is not configured.")
        return value


def test_credential_manager_resolves_validated_credentials() -> None:
    manager = CredentialManager(_SecretManager({"MANGA_DIRECTOR_TOKEN": "credential-value"}))

    assert manager.get("MANGA_DIRECTOR_TOKEN") == "credential-value"


def test_credential_reference_never_contains_the_secret_value() -> None:
    manager = CredentialManager(_SecretManager({"MANGA_DIRECTOR_TOKEN": "credential-value"}))

    reference = manager.reference("MANGA_DIRECTOR_TOKEN")

    assert reference.name == "MANGA_DIRECTOR_TOKEN"
    assert reference.required is True
    assert reference.configured is True
    assert "credential-value" not in repr(reference)


def test_credential_reference_reports_optional_missing_credentials() -> None:
    manager = CredentialManager(_SecretManager({}))

    reference = manager.reference("MANGA_DIRECTOR_TOKEN", required=False)

    assert reference.configured is False


def test_credential_manager_rejects_unsafe_credential_names() -> None:
    manager = CredentialManager(_SecretManager({}))

    with pytest.raises(ConfigurationError, match="uppercase"):
        manager.get("../MANGA_DIRECTOR_TOKEN")
