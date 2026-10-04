from manga_director.cli.config import (
    CONFIGURATION_SCHEMA_VERSION,
    AppConfig,
    configuration_fingerprint,
    configuration_governance,
)


def test_configuration_governance_reports_integrity_and_stable_safe_fingerprint() -> None:
    config = AppConfig(database_url="postgresql://user:password@example.test/db")

    report = configuration_governance(config)

    assert report.schema_version == CONFIGURATION_SCHEMA_VERSION
    assert report.compatible is True
    assert report.integrity_valid is True
    assert report.fingerprint == configuration_fingerprint(config)
    assert "password" not in report.fingerprint


def test_configuration_governance_flags_schema_migration_without_rejecting_legacy_config() -> None:
    report = configuration_governance(AppConfig(schema_version="0"))

    assert report.compatible is False
    assert report.migration_required is True
