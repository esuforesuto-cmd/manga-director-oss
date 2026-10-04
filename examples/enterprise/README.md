# Enterprise Planning Example

Use a configuration profile that references environment-managed secrets; do
not put API keys, database passwords, or webhook secrets in `config.yaml`.

Before enabling an Enterprise-oriented adapter, review
[Enterprise Readiness](../../docs/ENTERPRISE.md), run `security validate`, and
record health/diagnostic evidence. This example intentionally contains no
production credentials or Cloud integration.
