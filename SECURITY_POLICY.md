# LTS Security Policy

## Scope

Security maintenance applies to the active `6.0.x` LTS line and its supported
public package, CLI, FastAPI/REST, MCP, Web UI, SDK, Extension, Marketplace,
and workflow boundaries.

## Response process

Report suspected vulnerabilities through the private process in
[SECURITY.md](SECURITY.md). Maintainers assess affected supported lines,
prepare a compatible remediation, validate it, and coordinate disclosure when
safe. Public issues must not contain exploit details, credentials, or private
project content.

## Compatibility boundary

Security fixes preserve the LTS public contract wherever possible. A mitigation
that requires a behavior change must document the risk, operator action, and
compatibility impact before release. External CVE review, hosted secret
scanning, signing, and publication remain maintainer-controlled operations.
