# Security Policy

## Supported maintenance line

Security fixes are considered for the current `6.0.x` LTS line and documented
supported maintenance lines. Do not report vulnerabilities through public
issues.

## Reporting a vulnerability

Use GitHub's private security advisory or reporting channel for this repository.
Include a minimal reproduction, affected version, impact, and any mitigation
you have identified. Do not include secrets, tokens, production project data,
or exploit payloads beyond what is necessary for reproduction.

## Response expectations

Maintainers will acknowledge a valid report, assess scope, and coordinate a
private fix before public disclosure where practical. Release timing depends on
severity and availability of a safe patch. Reporters should provide affected
versions, impact, a minimal reproduction, and safe mitigation details.

## Security boundaries

The StateMachine remains authoritative for workflow transitions. v6.x Platform,
SDK, Extension, Marketplace, Governance, and Observability reports are local,
human-gated, and non-enforcing. They do not authorize remote extension
installation, Marketplace publication, automatic approval, or workflow bypass.
FastAPI, MCP, and the Web UI remain outer delivery boundaries and must not
bypass workflow validation.
