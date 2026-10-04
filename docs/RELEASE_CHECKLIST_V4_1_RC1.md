# v4.1 RC1 Release Checklist

## Local evidence

- [x] Canonical Python version set to `4.1.0rc1`.
- [x] Derived OpenAPI and MCP version metadata use the package version source.
- [x] Frontend prerelease metadata and SBOM are aligned.
- [x] Regression, compatibility, integration, architecture, benchmark, security,
  documentation, and quality-gate checks pass locally.
- [x] Local wheel/sdist build and Twine metadata validation pass for `4.1.0rc1`.
- [x] No StateMachine, Workflow, Repository, Provider, Backend, or delivery
  contract was replaced.

## Required before publication

- [ ] Run exact-tag hosted CI.
- [ ] Run dependency/CVE and secret scans.
- [ ] Review resolved dependency licenses.
- [ ] Rebuild and validate wheel/sdist from the approved release commit.
- [ ] Review RC feedback and approve publication.
