# v4.8.0 Security Audit

## Review scope

- Pydantic DTO validation for v4.8 reports and policies.
- StateMachine workflow-boundary regression coverage.
- Import boundary review for no execution, service routing, telemetry,
  persistence, or external connectivity path.
- Local dependency audit of installed, non-editable dependencies.

## Result

The local audit reported no known vulnerabilities for auditable installed
dependencies. The editable `manga-director` project itself is not published as
a dependency during the audit and is therefore excluded from vulnerability
matching. No new Provider, Backend, network, credential, execution, or
automatic approval path is introduced by this final release.

## Residual release responsibility

Protected CI security scans, artifact signing, publishing credentials, and
post-publication vulnerability monitoring require maintainer authority.

