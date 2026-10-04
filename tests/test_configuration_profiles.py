"""Compatibility tests for configuration-layer profiles and safe operations."""

import json
from pathlib import Path

import pytest
import yaml

from manga_director.cli.config import (
    AppConfig,
    clear_config_cache,
    configuration_diff,
    configuration_snapshot,
    export_configuration,
    load_config,
    require_writable_configuration,
)
from manga_director.domain.exceptions import ConfigurationError


def test_named_profile_merges_without_core_configuration(tmp_path: Path) -> None:
    path = tmp_path / "profile-fixture.yaml"
    content = """profile: testing
log_level: INFO
profiles:
  testing:
    optimizer_enabled: false
  enterprise:
    repository:
      root: enterprise-projects
"""

    try:
        path.write_text(content, encoding="utf-8")
        clear_config_cache(path)
        testing = load_config(path)
        enterprise = load_config(path, profile="enterprise")
    finally:
        path.unlink(missing_ok=True)

    assert testing.profile == "testing"
    assert testing.optimizer_enabled is False
    assert enterprise.profile == "enterprise"
    assert enterprise.read_only is True
    assert enterprise.repository.root == Path("enterprise-projects")


def test_environment_overrides_apply_in_configuration_layer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    monkeypatch.setenv("MANGA_DIRECTOR_PROFILE", "offline")
    monkeypatch.setenv("MANGA_DIRECTOR__LOG_LEVEL", "ERROR")
    monkeypatch.setenv("MANGA_DIRECTOR__REPOSITORY__ROOT", "offline-projects")
    clear_config_cache(path)

    config = load_config(path)

    assert config.profile == "offline"
    assert config.default_llm_provider == "mock"
    assert config.log_level == "ERROR"
    assert config.repository.root == Path("offline-projects")


def test_safe_snapshot_diff_and_export_redact_sensitive_configuration() -> None:
    before = AppConfig(database_url="postgresql://user:password@example.test/db")
    after = AppConfig(profile="enterprise", read_only=True, log_level="WARNING")

    snapshot = configuration_snapshot(before)
    difference = configuration_diff(before, after)

    assert snapshot.values["database_url"] == "[redacted]"
    assert "password" not in json.dumps(snapshot.values)
    assert difference.profile_after == "enterprise"
    assert "log_level" in difference.changes
    assert yaml.safe_load(export_configuration(snapshot))["profile"] == "development"
    assert json.loads(export_configuration(snapshot, format="json"))["read_only"] is False


def test_unknown_profile_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="Unsupported configuration profile"):
        load_config(tmp_path / "missing.yaml", profile="unsupported")


def test_enterprise_profile_smoke_is_read_only_and_snapshot_safe(tmp_path: Path) -> None:
    config = load_config(tmp_path / "enterprise.yaml", profile="enterprise")

    assert config.read_only is True
    assert configuration_snapshot(config).read_only is True
    with pytest.raises(ConfigurationError, match="read-only"):
        require_writable_configuration(config)
