# v3.1.0 RC1 Security Audit

The RC retains validation/redaction controls for secrets, webhook signatures,
SSRF, injection, Knowledge/template/manifest input, Plugin/Extension validation,
rate limits, audit logs, and configuration. v3.1 diagnostic reports expose no
metadata or configuration values and perform no external calls.

Hosted dependency/CVE audit, secret scan, and npm audit must run against the
exact `v3.1.0rc1` tag before publication. Local review does not substitute for
those publication-time checks.
