# OSS Readiness

The v2.5 readiness facade checks local contribution, governance, license, and
community documents without contacting GitHub or any external service. It is
evidence for maintainers, not an automated publication workflow.

`ReleaseReadiness.oss_readiness_report()` verifies the contribution guide,
code of conduct, governance, maintainers, security policy, supported versions,
MIT license, and dependency-license report. The resulting DTO is available as
JSON or Markdown to any delivery adapter.

Review the report before release alongside [Contributing](../CONTRIBUTING.md),
[Security](../SECURITY.md), and the [Dependency Policy](DEPENDENCY_POLICY.md).
