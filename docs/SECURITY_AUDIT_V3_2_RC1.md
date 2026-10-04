# v3.2.0 RC1 Security Audit

The RC retains validation and redaction controls for secrets, webhook
signatures, SSRF, injection, Knowledge/Asset/template/manifest input,
Plugin/Extension validation, rate limits, audit logs, and configuration. v3.2
reports expose no metadata or configuration values and perform no external
calls.

Local `pip-audit` reported no known vulnerabilities for resolvable declared
dependencies (the local unpublished package itself is intentionally skipped),
and `npm audit --omit=dev --audit-level=high` reported no vulnerabilities.

Hosted dependency/CVE audit, secret scan, and npm audit must run against the
exact `v3.2.0rc1` tag before publication. Local review does not substitute for
those publication-time checks.
