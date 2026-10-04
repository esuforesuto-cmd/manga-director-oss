# Enterprise Configuration Operations

Use the `enterprise` profile as a controlled baseline, then apply only
validated `profiles:` overrides and environment-managed secrets. Never put API
keys, webhook secrets, access keys, tokens, or database passwords in
`config.yaml`.

Before rollout:

1. Load the target profile and create a redacted `ConfigurationSnapshot`.
2. Compare it with the previous profile using `configuration_diff`.
3. Export the redacted snapshot for approval/audit evidence.
4. Keep `read_only: true` until an approved configuration change is applied.
5. Run security, health, diagnostics, Repository integrity, and mock-provider
   checks in the target environment.

This guidance does not add cloud configuration, distributed configuration, SSO,
or an Automation runtime.
