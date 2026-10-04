# Iteration 2 Quality Report

## Scope

Iteration 2 made no product feature, provider, workflow, database, or UI
change. It preserved the existing public API and the mandatory one-page,
forward-only workflow rules.

## Improvements

- Normalized notification, security, and Extension SDK modules to the project
  style, and corrected transient notification retry behavior for transport
  failures without status codes.
- Added architecture, public-import, dependency, local documentation-link, and
  benchmark-smoke tests.
- Made local-file project listing deterministic and retained atomic file writes.
- Moved PostgreSQL and Alembic tooling into explicit optional extras; SQLite
  remains available through the base SQLAlchemy dependency.
- Added pip caching, parallel static-analysis/test jobs, coverage XML output,
  a retained CI artifact, and a cached frontend CI job.
- Added performance, profiling, error-handling, and logging operational guides.
- Restored a non-interactive frontend lint gate, added a `typecheck` command,
  and replaced internal HTML navigation links with framework navigation links
  without changing the rendered UI.

## Architecture review

The Domain layer has no outward dependency on workflow, delivery, adapters, or
repositories. The Page `WorkflowEngine` does not import delivery adapters,
repository implementations, provider adapters, or Agents. It continues to
operate through typed contracts and the StateMachine remains the authority for
every state transition.

Repository implementations remain behind `ProjectRepository`; the local-file
adapter retains JSON/YAML serialization, validation-before-save, and atomic
replacement. Database code remains an infrastructure adapter and the CLI,
workflow, and Agents do not select concrete database classes.

## Verification

The available local environment completed:

- `ruff check src tests`
- `mypy src`
- `pytest` (including architecture, import, dependency, documentation-link,
  and benchmark smoke tests)
- `npm run lint`, `npm run typecheck`, `npm run test`, and `npm run build`
- `npm audit --omit=dev --json` with zero production dependency findings

The CI workflow installs the development extra and additionally produces a
coverage XML artifact on Python 3.11 while retaining Python 3.11/3.12 test
coverage. Local coverage execution requires the `pytest-cov` development
dependency to be installed.

## Known baseline limitation

Automation is referenced by longer-term planning but there is no Automation
runtime package in this source baseline. It was therefore not invented or
benchmarked in this maintenance-only iteration.
