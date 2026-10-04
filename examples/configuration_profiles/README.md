# Configuration Profiles Planning Example

Treat configuration profiles as environment-specific overlays with shared safe
defaults. Secret values come from environment variables or a Secret Provider,
not `config.yaml`. Preserve existing defaults and validate profile compatibility
before rollout; see [Enterprise Readiness](../../docs/ENTERPRISE.md).
