# v2.7.0 RC1 Security Audit

The RC retains existing controls for secret/configuration redaction, webhook
validation, SSRF and URL controls, input validation, output sanitization, rate
limiting, audit logging, Plugin and Extension manifest validation, and error
masking. Director and Knowledge reports operate on safe local DTO data,
repository metadata keys, and bounded public evidence; they do not expose
metadata values, hidden reasoning, or external service responses.

Local tests cover these boundaries. Hosted dependency/CVE audit and secret scan
remain mandatory release gates for the exact `v2.7.0rc1` tag; local review does
not replace those hosted scans.
