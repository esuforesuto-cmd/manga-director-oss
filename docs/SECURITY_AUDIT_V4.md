# v4.0.0 Security Audit

v4.0.0 retains secret/configuration redaction, DTO/input validation, existing
SSRF and webhook boundaries, injection-safe persistence, memory validation,
graph-integrity checks, Plugin and Extension manifest validation, rate limits,
and audit boundaries. v4 reports expose bounded DTO evidence only and cannot
mutate content, persist memory or graph evidence, enforce policy, retain an
audit record, authorize, generate, complete review, or approve.

Local boundary and validation tests pass. A local dependency audit found no
known vulnerabilities in auditable installed dependencies; the local editable
package is not present on PyPI and is skipped by that tool. Exact-tag
dependency/CVE audit, secret scan, and hosted security workflow remain required
before publication; those external gates are not represented as a local pass
claim.
