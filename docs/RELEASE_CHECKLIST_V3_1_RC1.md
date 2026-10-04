# v3.1.0 RC1 Release Checklist

## Completed locally

- [x] Canonical version, root import, MCP, optional OpenAPI, frontend, SBOM,
  README, changelog, and RC notes are aligned.
- [x] Architecture, compatibility, workflow, Creative, Knowledge, Operations,
  DX, reliability, diagnostics, reporting, security, package, and benchmark
  evidence is documented.
- [x] Ruff, strict mypy, pytest, frontend lint/typecheck/test/build, wheel/sdist,
  Twine, clean-install CLI/MCP smoke, provider-free example/benchmark smoke, and
  direct Python/frontend dependency audits pass.
- [x] Governance, license, supported-version, security, contribution, and CI
  assets are present.

## Required before publication

- [ ] Confirm hosted backend, frontend, docs, package, security, release,
  nightly, benchmark, Creative, Knowledge, Operations, DX, diagnostics,
  production, and enterprise jobs.
- [ ] Run hosted dependency/CVE and secret scans against the exact RC tag.
- [ ] Repeat wheel/sdist, Twine, and clean-install smoke in the tagged release
  environment.
- [ ] Publish only approved `v3.1.0rc1` prerelease artifacts and tag.

## Scope gate

- [x] No new workflow, Provider, Backend, cloud, marketplace, distributed
  runtime, autonomous AI, automatic review, automatic approval, or breaking
  public contract was introduced.
