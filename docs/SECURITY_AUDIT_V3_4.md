# v3.4.0 Security Audit

Local release validation retains secret redaction, SSRF and webhook controls,
injection defenses, manifest/Plugin/Extension validation, configuration
validation, rate-limit and audit checks. The v3.4 reporting DTOs do not add
network, persistence, execution, deployment, or approval authority.

Direct Python dependency audit and production frontend dependency audit report
no known vulnerabilities in the validated local environment. Hosted dependency,
CVE, and secret scans must still run against the exact `v3.4.0` tag before
publication.
