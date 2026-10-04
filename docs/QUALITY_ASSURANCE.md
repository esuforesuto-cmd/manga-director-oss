# Quality Assurance

## Quality model

Every accepted v2.5 implementation Issue must demonstrate architecture,
compatibility, security, documentation, and rollback evidence in addition to
its focused tests. Mock/local fixtures are required; live credentials and
network calls are excluded from CI.

## Required checks

1. Run Ruff, strict mypy, pytest with coverage, architecture/import checks, and
   documentation-link checks.
2. Run provider-free benchmark smoke for the affected boundary and record the
   environment when comparing results.
3. Run public API, CLI, MCP, Repository, Plugin, Extension SDK, Provider, and
   Backend compatibility tests where affected.
4. Run security validation, sanitization, audit, manifest, dependency, and
   secret-scan gates.
5. For production work, run health, diagnostics, recovery, integrity, startup,
   shutdown, and explicit-approval fixtures.

## Non-negotiable workflow checks

The StateMachine remains authoritative. Tests must prove exactly one Page per
execution, no skipped stage, storyboard before generation, quality before
approval, and no implicit approval from `run`.

See [Quality Gates](QUALITY_GATES.md) for the CI gate inventory.

## v4.3 Iteration 3 QA foundation

`V43ProductionOperationsService.quality_assurance()` adds immutable QA Session,
Validation Rule, Review Checklist, Quality Score, and QA Summary DTOs. It makes
the storyboard and quality-review prerequisites visible, but does not start a
session, evaluate a rule, complete a checklist, set a score, remediate, pass a
gate, grant approval, or change a workflow.
