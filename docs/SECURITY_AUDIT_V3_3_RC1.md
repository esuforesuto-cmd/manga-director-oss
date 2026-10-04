# v3.3.0 RC1 Security Audit

The RC retains existing controls for secret/configuration redaction, input and
manifest validation, SSRF/webhook boundaries, injection-safe persistence,
Plugin and Extension validation, rate limiting, audit boundaries, and DTO-only
transport delivery. v3.3 Asset and Governance reports expose no metadata values
and have no mutation, retention, archive, or delete authority.

Local security and boundary tests pass. The declared Python dependency audit and
production frontend dependency audit report no known vulnerabilities. Secret
scanning and the hosted security workflow must still be repeated for the exact
`v3.3.0rc1` tag before publication; local review is not a substitute for those
release gates.
