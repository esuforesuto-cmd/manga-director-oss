from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from manga_director.domain.exceptions import ConfigurationError

_ENVIRONMENT_REFERENCE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


@dataclass(frozen=True)
class _CachedConfig:
    file_stamp: tuple[int, int] | None
    environment: tuple[tuple[str, str | None], ...]
    config: AppConfig


_CONFIG_CACHE: dict[tuple[Path, str], _CachedConfig] = {}

_PROFILE_DEFAULTS: dict[str, dict[str, Any]] = {
    "development": {"log_level": "DEBUG"},
    "testing": {"log_level": "WARNING"},
    "production": {"log_level": "INFO"},
    "enterprise": {"log_level": "INFO", "read_only": True},
    "offline": {"default_image_generator": "mock", "default_llm_provider": "mock"},
}
_ENVIRONMENT_OVERRIDE_PREFIX = "MANGA_DIRECTOR__"
_SENSITIVE_CONFIGURATION_KEYS = ("secret", "token", "password", "api_key", "access_key")
CONFIGURATION_SCHEMA_VERSION = "1"


class RepositorySettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    driver: str = "local_file"
    root: Path = Path(".manga-director")
    format: Literal["json", "yaml"] = "json"


class AppConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile: str = "development"
    schema_version: str = CONFIGURATION_SCHEMA_VERSION
    read_only: bool = False
    default_image_generator: str = "mock"
    default_llm_provider: str = "mock"
    default_prompt_template: str = "image_prompt.md"
    optimizer_enabled: bool = True
    validation_enabled: bool = True
    prompt_directory: Path | None = None
    log_level: str = "INFO"
    repository: RepositorySettings = Field(default_factory=RepositorySettings)
    database_provider: str | None = None
    database_url: str | None = None
    plugin_directory: Path = Path("plugins")


class ConfigurationSnapshot(BaseModel):
    """A safe, immutable configuration view suitable for diagnostics or export."""

    model_config = ConfigDict(frozen=True)

    profile: str
    source: str | None = None
    read_only: bool
    values: dict[str, Any] = Field(default_factory=dict)


class ConfigurationDiff(BaseModel):
    """Explicit before/after values for compatible configuration review."""

    model_config = ConfigDict(frozen=True)

    profile_before: str
    profile_after: str
    changes: dict[str, tuple[Any, Any]] = Field(default_factory=dict)


class ConfigurationGovernanceReport(BaseModel):
    """Version, compatibility, and integrity assessment for safe rollout."""

    model_config = ConfigDict(frozen=True)

    schema_version: str
    expected_schema_version: str
    compatible: bool
    migration_required: bool
    integrity_valid: bool
    fingerprint: str
    messages: tuple[str, ...] = ()


class ConfigurationImportValidation(BaseModel):
    """Safe validation result for an imported configuration snapshot or mapping."""

    model_config = ConfigDict(frozen=True)

    valid: bool
    profile: str | None = None
    fingerprint: str | None = None
    messages: tuple[str, ...] = ()


def load_config(path: Path, profile: str | None = None) -> AppConfig:
    """Load config.yaml, using safe defaults when it has not yet been created."""
    resolved = path.resolve()
    stamp = _file_stamp(path)
    selected_profile = profile or os.environ.get("MANGA_DIRECTOR_PROFILE") or "development"
    cache_key = (resolved, selected_profile)
    cached = _CONFIG_CACHE.get(cache_key)
    if cached is not None and cached.file_stamp == stamp and _environment_matches(cached.environment):
        return cached.config
    if stamp is None:
        defaults = _profile_defaults(selected_profile)
        defaults["profile"] = selected_profile
        defaults = _deep_merge(defaults, _environment_overrides())
        config = AppConfig.model_validate(_merge_defaults(defaults))
        _CONFIG_CACHE[cache_key] = _CachedConfig(None, _configuration_environment(), config)
        return config
    try:
        content = path.read_text(encoding="utf-8")
        raw: Any = yaml.safe_load(content) or {}
        if not isinstance(raw, dict):
            raise ValueError("configuration root must be a mapping")
        raw_profile = raw.get("profile", selected_profile)
        if profile is None and "MANGA_DIRECTOR_PROFILE" not in os.environ:
            selected_profile = str(raw_profile)
            cache_key = (resolved, selected_profile)
        profiles = raw.pop("profiles", {})
        if profiles and not isinstance(profiles, dict):
            raise ValueError("profiles must be a mapping")
        profile_override = profiles.get(selected_profile, {}) if isinstance(profiles, dict) else {}
        if not isinstance(profile_override, dict):
            raise ValueError(f"profile '{selected_profile}' must be a mapping")
        merged = _deep_merge(_profile_defaults(selected_profile), _expand_environment(raw))
        merged = _deep_merge(merged, _expand_environment(profile_override))
        merged = _deep_merge(merged, _environment_overrides())
        merged["profile"] = selected_profile
        environment = tuple(
            sorted(
                (name, os.environ.get(name))
                for name in {*_ENVIRONMENT_REFERENCE.findall(content), *_configuration_environment_names()}
            )
        )
        config = AppConfig.model_validate(_merge_defaults(merged))
        _CONFIG_CACHE[cache_key] = _CachedConfig(stamp, environment, config)
        return config
    except (OSError, ValueError, yaml.YAMLError, ValidationError) as exc:
        raise ConfigurationError(f"Unable to load configuration '{path}': {exc}") from exc


def write_default_config(path: Path) -> AppConfig:
    config = load_config(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        data = config.model_dump(mode="json")
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return config


def clear_config_cache(path: Path | None = None) -> None:
    """Invalidate cached validated config after a controlled runtime reload."""

    if path is None:
        _CONFIG_CACHE.clear()
    else:
        resolved = path.resolve()
        for key in [key for key in _CONFIG_CACHE if key[0] == resolved]:
            _CONFIG_CACHE.pop(key, None)


def configuration_diagnostics(path: Path | None = None) -> dict[str, object]:
    """Expose safe cache metadata without returning configuration values or secrets."""

    entries = [key for key in _CONFIG_CACHE if path is None or key[0] == path.resolve()]
    cached = list(entries)
    return {"cache_entries": len(_CONFIG_CACHE), "requested_cached": len(cached)}


def configuration_snapshot(config: AppConfig, source: Path | None = None) -> ConfigurationSnapshot:
    """Capture a safe snapshot without exposing configured credentials or URLs."""

    values = _redact_configuration(config.model_dump(mode="json"))
    return ConfigurationSnapshot(
        profile=config.profile,
        source=str(source) if source is not None else None,
        read_only=config.read_only,
        values=values,
    )


def configuration_diff(before: AppConfig, after: AppConfig) -> ConfigurationDiff:
    """Return a flattened, redacted diff for review before configuration rollout."""

    before_values = _flatten(_redact_configuration(before.model_dump(mode="json")))
    after_values = _flatten(_redact_configuration(after.model_dump(mode="json")))
    changes = {
        key: (before_values.get(key), after_values.get(key))
        for key in sorted(set(before_values) | set(after_values))
        if before_values.get(key) != after_values.get(key)
    }
    return ConfigurationDiff(
        profile_before=before.profile,
        profile_after=after.profile,
        changes=changes,
    )


def export_configuration(snapshot: ConfigurationSnapshot, format: Literal["json", "yaml"] = "yaml") -> str:
    """Export only the safe configuration snapshot in a portable format."""

    if format == "json":
        return snapshot.model_dump_json(indent=2)
    return str(yaml.safe_dump(snapshot.model_dump(mode="json"), sort_keys=False))


def validate_configuration_import(
    content: str, format: Literal["json", "yaml"] = "yaml"
) -> ConfigurationImportValidation:
    """Validate imported, portable configuration data without applying a change."""

    try:
        parsed: Any = json.loads(content) if format == "json" else yaml.safe_load(content)
        if not isinstance(parsed, dict):
            raise ValueError("configuration import root must be a mapping")
        values = parsed.get("values", parsed)
        if not isinstance(values, dict):
            raise ValueError("configuration import values must be a mapping")
        candidate = AppConfig.model_validate(_merge_defaults(values))
        governance = configuration_governance(candidate)
        messages = governance.messages
        return ConfigurationImportValidation(
            valid=governance.compatible and governance.integrity_valid,
            profile=candidate.profile,
            fingerprint=governance.fingerprint,
            messages=messages,
        )
    except (json.JSONDecodeError, ValueError, yaml.YAMLError, ValidationError) as exc:
        return ConfigurationImportValidation(valid=False, messages=(str(exc),))


def require_writable_configuration(config: AppConfig) -> None:
    """Guard optional configuration writes without introducing Core-layer policy."""

    if config.read_only:
        raise ConfigurationError(f"Configuration profile '{config.profile}' is read-only.")


def configuration_fingerprint(config: AppConfig) -> str:
    """Return a stable, secret-safe digest for configuration change control."""

    snapshot = configuration_snapshot(config)
    payload = snapshot.model_dump_json(by_alias=True, exclude_none=False)
    return sha256(payload.encode("utf-8")).hexdigest()


def configuration_governance(config: AppConfig) -> ConfigurationGovernanceReport:
    """Check current schema compatibility and validated configuration integrity."""

    compatible = config.schema_version == CONFIGURATION_SCHEMA_VERSION
    messages: list[str] = []
    if not compatible:
        messages.append(
            f"Configuration schema '{config.schema_version}' requires migration to "
            f"'{CONFIGURATION_SCHEMA_VERSION}'."
        )
    try:
        AppConfig.model_validate(config.model_dump(mode="python"))
    except ValidationError as exc:
        integrity_valid = False
        messages.append(f"Integrity validation failed: {exc}")
    else:
        integrity_valid = True
    return ConfigurationGovernanceReport(
        schema_version=config.schema_version,
        expected_schema_version=CONFIGURATION_SCHEMA_VERSION,
        compatible=compatible,
        migration_required=not compatible,
        integrity_valid=integrity_valid,
        fingerprint=configuration_fingerprint(config),
        messages=tuple(messages),
    )


def _file_stamp(path: Path) -> tuple[int, int] | None:
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    return (stat.st_mtime_ns, stat.st_size)


def _environment_matches(snapshot: tuple[tuple[str, str | None], ...]) -> bool:
    return all(os.environ.get(name) == value for name, value in snapshot)


def _expand_environment(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, list):
        return [_expand_environment(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand_environment(item) for key, item in value.items()}
    return value


def _merge_defaults(raw: dict[str, Any]) -> dict[str, Any]:
    """Merge optional nested sections with model defaults before validation."""

    defaults = AppConfig().model_dump(mode="python")
    return _deep_merge(defaults, raw)


def _deep_merge(defaults: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(defaults)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _profile_defaults(profile: str) -> dict[str, Any]:
    try:
        defaults = _PROFILE_DEFAULTS[profile]
    except KeyError as exc:
        raise ConfigurationError(f"Unsupported configuration profile: {profile}") from exc
    return _deep_merge({}, defaults)


def _configuration_environment_names() -> set[str]:
    return {name for name in os.environ if name == "MANGA_DIRECTOR_PROFILE" or name.startswith(_ENVIRONMENT_OVERRIDE_PREFIX)}


def _configuration_environment() -> tuple[tuple[str, str | None], ...]:
    return tuple(sorted((name, os.environ.get(name)) for name in _configuration_environment_names()))


def _environment_overrides() -> dict[str, Any]:
    values: dict[str, Any] = {}
    for name, raw_value in os.environ.items():
        if not name.startswith(_ENVIRONMENT_OVERRIDE_PREFIX):
            continue
        keys = [part.lower() for part in name.removeprefix(_ENVIRONMENT_OVERRIDE_PREFIX).split("__") if part]
        if not keys:
            continue
        target = values
        for key in keys[:-1]:
            target = target.setdefault(key, {})
        target[keys[-1]] = yaml.safe_load(raw_value)
    return values


def _redact_configuration(value: Any, key: str = "") -> Any:
    if key.lower() in _SENSITIVE_CONFIGURATION_KEYS or "database_url" == key.lower():
        return "[redacted]" if value is not None else None
    if isinstance(value, dict):
        return {item_key: _redact_configuration(item, item_key) for item_key, item in value.items()}
    if isinstance(value, list):
        return [_redact_configuration(item) for item in value]
    return value


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if not isinstance(value, dict):
        return {prefix: value}
    flattened: dict[str, Any] = {}
    for key, item in value.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            flattened.update(_flatten(item, name))
        else:
            flattened[name] = item
    return flattened
