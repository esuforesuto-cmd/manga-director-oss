# Testing

Tests are grouped by behavior. Add a regression test for every fix, use
in-memory providers for deterministic tests, and preserve the page-at-a-time
approval invariant. Run `make coverage` before a release.

The release suite uses pytest, branch coverage, architecture/import/dependency
guards, local documentation-link validation, and a provider-free benchmark
smoke test.

```bash
PYTHONPATH=src python -m pytest --cov=manga_director --cov-report=term-missing
```

Coverage has an 80% project-wide minimum. It is a release safety net, not a
substitute for contract tests on workflow, persistence, adapters, and delivery
boundaries. The CI matrix runs the suite on Python 3.11 and 3.12.

## Platform authority coverage

`requires_windows_page_authority` is a test-level marker for a premise that
requires the canonical Windows page execution fence, R05 asset lease, or R26
proof chain. Those tests run normally on Windows and are skipped individually
on non-Windows systems because Linux must fail closed rather than emulate page
authority. Do not apply this marker to a module, directory, or a count-based
selection.

Linux remains supported for all non-page-authority behavior. In particular,
Linux tests must retain the fail-closed checks for durable entry points and may
not introduce a substitute fence, lease, proof, or mutation path.

The Windows full-regression CI matrix runs the complete pytest suite with
strict marker validation on Python 3.11 and 3.12. The 3.11 leg also produces
the project coverage report; the existing Windows mypy and path-containment
security coverage remain separate checks.
