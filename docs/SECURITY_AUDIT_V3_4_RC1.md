# v3.4.0 RC1 Security Audit

The RC retains existing controls for secret/configuration redaction, input and
manifest validation, SSRF/webhook boundaries, injection-safe persistence,
Knowledge/Asset validation, Plugin and Extension validation, rate limiting,
audit boundaries, and DTO-only transport delivery. v3.4 Knowledge and
Governance reports expose no metadata values and have no mutation, retention,
archive, delete, personnel-action, deployment, or publication authority.

Local security and boundary tests pass. The declared Python dependency audit and
production frontend dependency audit must still be repeated for the exact
`v3.4.0rc1` tag, together with secret scanning and the hosted security workflow,
before publication.
