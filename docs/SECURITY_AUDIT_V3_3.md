# v3.3.0 Security Audit

The release retains secret/configuration redaction, input and manifest
validation, SSRF/webhook boundaries, injection-safe persistence, Plugin and
Extension validation, rate limiting, audit boundaries, and DTO-only transport
delivery. Asset and Governance reports expose no metadata values and have no
mutation, retention, archive, or delete authority.

Local security and boundary tests pass. The declared Python dependency audit
and production frontend dependency audit report no known vulnerabilities.
Secret scanning and hosted security jobs must still run against the exact
`v3.3.0` tag before publication; local review is not a substitute for those
release gates.
