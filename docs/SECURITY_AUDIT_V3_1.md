# v3.1.0 Security Audit

v3.1.0 retains validation and redaction controls for secrets, webhook
signatures, SSRF, injection, Knowledge/template/manifest input,
Plugin/Extension validation, rate limits, audit logs, and configuration. Its
diagnostic reports expose no secret configuration values and perform no external
calls.

Direct Python and frontend dependency audits reported no known vulnerabilities
during local release validation. Hosted dependency/CVE audit and secret scan
must still run against the exact `v3.1.0` tag before publication.
