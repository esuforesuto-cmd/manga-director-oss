# v3.5.0 RC1 Security Audit

The RC retains secret/configuration redaction, DTO/input validation, existing
SSRF and webhook boundaries, injection-safe persistence, Knowledge validation
and graph-integrity boundaries, Plugin and Extension manifest validation, rate
limiting, and audit boundaries. v3.5 reports expose no metadata values and have
no mutation, graph persistence, policy enforcement, durable audit,
authorization, monitoring, deployment, or publication authority.

Local boundary and validation tests pass. A local `pip-audit` run reported no
known vulnerabilities for auditable dependencies; its editable local
`manga-director` distribution is not present on PyPI and is therefore skipped
by that tool. The exact-tag dependency/CVE audit, secret scan, and hosted
security workflow must be repeated before publication. Those external gates are
deliberately not represented as a local pass claim.
