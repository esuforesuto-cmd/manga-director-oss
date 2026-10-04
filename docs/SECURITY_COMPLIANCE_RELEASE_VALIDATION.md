# Security Compliance and Release Validation

`SecurityComplianceValidator` composes the existing security-monitoring
snapshot with caller-supplied control evidence. It verifies coverage of five
required areas: authentication, authorization, credential handling, audit, and
incident response.

`release_ready` is true only when the underlying audit is valid, no human
response is required, every required area has a compliant control, and no
supplied control is noncompliant. Reports expose only control IDs and area
status; evidence references and secret values are not returned.

Control identifiers and areas are validated at runtime before readiness is
calculated.

Validation is advisory and read-only. It never publishes a package, creates a
tag, uploads an artifact, changes a policy, or resolves an incident. The report
always records `release_performed=False`.
