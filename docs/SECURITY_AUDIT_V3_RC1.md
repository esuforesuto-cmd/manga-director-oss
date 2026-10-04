# v3.0.0 RC1 Security Audit

RC1 retains secret/configuration redaction, webhook validation, SSRF and URL
controls, input validation, output sanitization, rate limiting, audit logging,
Plugin and Extension manifest validation, and error masking. Director, Creative,
Knowledge, Review, and Readiness reports expose bounded public DTO evidence;
they do not expose metadata values, hidden reasoning, credentials, or external
service responses.

Local tests cover these boundaries. Hosted dependency/CVE audit and secret scan
remain mandatory gates for the exact `v3.0.0rc1` tag; local review does not
replace those publication-time scans.
