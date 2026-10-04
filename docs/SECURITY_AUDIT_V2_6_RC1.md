# v2.6.0 RC1 Security Audit

The RC retains existing controls for secret/configuration redaction, webhook
validation, SSRF and URL controls, input validation, output sanitization,
rate limiting, audit logging, Plugin and Extension manifest validation, and
error masking. Planning, analysis, provider governance, and Enterprise reports
operate on safe local DTO data and do not contact external services.

The RC updates the development `pytest` constraint to `>=9.0.3,<10` in response
to the dependency-audit finding for pytest 8.4.2. This does not alter the
runtime dependency set or public package API.

Local tests cover these boundaries. Hosted dependency/CVE audit and secret scan
remain mandatory release gates for the exact `v2.6.0rc1` tag; this repository
does not claim that a local review replaces those hosted scans.
