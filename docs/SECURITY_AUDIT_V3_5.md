# v3.5.0 Security Audit

v3.5.0 retains secret/configuration redaction, DTO/input validation, SSRF and
webhook boundaries, injection-safe persistence, Knowledge validation and graph
integrity boundaries, Plugin and Extension manifest validation, rate limiting,
and audit boundaries. v3.5 reports expose no metadata values and have no graph
persistence, policy enforcement, durable audit, authorization, monitoring,
deployment, or publication authority.

Local boundary and validation tests pass. Local `pip-audit` reports no known
vulnerabilities for auditable dependencies; the local editable
`manga-director` distribution is not present on PyPI and is skipped by that
tool. Publication still requires the exact-tag dependency/CVE audit, secret
scan, and hosted security workflow.
