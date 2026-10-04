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
