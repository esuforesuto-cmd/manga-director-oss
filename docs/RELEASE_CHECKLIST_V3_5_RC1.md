# v3.5.0 RC1 Release Checklist

## Completed locally

- [x] Version source set to `3.5.0rc1`; MCP and optional OpenAPI derive it.
- [x] Frontend prerelease metadata set to `3.5.0-rc.1`.
- [x] v3.5 architecture and compatibility reviews recorded.
- [x] v3.5 Foundation, Intelligence, Governance, integration, and regression
  tests pass without mutating a workflow or Repository.
- [x] Static analysis, compilation, provider-free benchmark smoke, and docs
  asset validation pass.
- [x] Frontend typecheck, unit contracts, and production build pass with the
  `3.5.0-rc.1` frontend metadata.

## Required before publication

- [ ] Run tagged hosted backend, frontend, package, docs, and release CI.
- [ ] Run exact-tag dependency/CVE audit and secret scan.
- [ ] Review reproducible RC feedback; accept only corrective, compatible fixes.
- [ ] Build and verify wheel/sdist from the RC tag.
- [ ] Create the `v3.5.0rc1` tag and publish the prerelease through the
  approved release workflow.
