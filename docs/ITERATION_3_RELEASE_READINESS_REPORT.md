# Iteration 3 Release Readiness Report

## Scope and compatibility

Iteration 3 introduced no product feature, Provider, Plugin, Workflow,
Database, UI behavior, or package version change. The package remains
`2.0.0rc1` on the `2.0.x` maintenance baseline. The root Python API, fixed
page state machine, explicit human approval, CLI workflow behavior, MCP tools,
persisted Project contract, and Web UI presentation contract remain compatible.

## Public API review

- Root package exports are documented in `docs/PUBLIC_API.md`; no root export
  is deprecated or removed.
- `__version__` is now a single internal source of truth and is included in the
  public export list for standard package introspection.
- MCP initialization reports the actual package version.
- Unexpected MCP transport errors are logged internally and rendered as a safe
  generic JSON-RPC error instead of exposing raw exception details.
- The Web UI has no Python/Core imports and its REST client is explicitly
  documented as requiring an external compatible HTTP service.

## Package and release validation

| Check | Result |
| --- | --- |
| Ruff / strict mypy | Passed (104 source files) |
| Pytest / branch coverage | Passed: 118 tests, 82.88%; minimum is 80% |
| Wheel and sdist build | Passed for `2.0.0rc1` |
| Twine metadata rendering | Passed |
| Wheel content | `plugins` package and `py.typed` verified present |
| Clean wheel installation | Passed |
| Installed CLI / MCP / Plugin commands | Passed (`--help`, `mcp tools`, `plugin list`) |
| SQLite Alembic migration | Passed at `0001_initial (head)` |
| Benchmark smoke | Passed in Iteration 2 and remains a CI/nightly gate |
| Web lint / typecheck / unit test / build | Passed; 4 frontend tests passed |

The packaging review found and fixed one release-blocking defect: the broad
`plugins/` ignore rule omitted the built-in plugin package from the wheel. The
rule is now root-scoped and the wheel validation prevents recurrence.

## Security review

- Resolved runtime dependency audit: no known vulnerabilities after using a
  current pip in an isolated audit environment.
- `npm audit --omit=dev` previously reported zero production findings; the CI
  security job repeats this audit.
- A source secret-pattern scan found no credential/private-key patterns.
- The CI security job adds `pip-audit` and Gitleaks. `SECURITY.md`, an SPDX 2.3
  SBOM, and a dependency license report are present.
- Webhook HTTPS/SSRF controls and output sanitization remain documented
  application-layer boundaries; no raw error details are returned by MCP
  transport failures.

## CI/CD and OSS operations

CI now separates static analysis, Python test matrix, frontend, package, and
security jobs with pip/npm caches and artifacts. A nightly workflow runs the
regression suite and benchmark smoke. A tag/manual release workflow builds and
validates distribution artifacts without publishing them. Community and
operational assets now include CONTRIBUTING, CODE_OF_CONDUCT, SECURITY,
SUPPORTED_VERSIONS, GOVERNANCE, MAINTAINERS, release notes, migration guide,
SBOM, license report, and release checklist.

## Release status

**Core distribution readiness: pass.** The Python package, CLI, MCP, Plugin
package content, local SQLite migration, documentation links, and Web UI
build/test quality gates are ready for a clean-environment CI release review.

**Full surface readiness requested for v2.1.0: conditional / not claimable.**
This source baseline contains no FastAPI/OpenAPI implementation and no
Automation runtime. Therefore FastAPI startup/API DTO validation and Automation
execution cannot honestly be certified without adding forbidden new features.
The Web UI remains a tested frontend scaffold, not a bundled production HTTP
application. These existing scope gaps are classified in `TECH_DEBT.md` and
must be addressed in a separately approved feature release before advertising
those surfaces as shipped.

## Remaining release actions

1. Run the configured GitHub Actions workflows from a clean hosted runner and
   review their artifacts.
2. Do not publish a v2.1.0 tag until the scope gate in the release checklist is
   explicitly accepted.
3. Schedule the existing FastAPI/security-middleware and notification/SDK debt
   items through the documented issue process; do not bypass workflow safety.
