# manga-director v2.5.0 RC1

## Overview

v2.5.0rc1 is the release candidate for the v2.5 stable line. It packages the
reviewed Production quality, observability, diagnostics, reliability, release,
and OSS readiness work without adding workflow stages or changing a documented
public contract.

## Improvements

- Read-only quality automation validates repository, workflow, configuration,
  API, documentation, release artifact, and version evidence.
- Transport-neutral observability, diagnostics, performance analysis, operations,
  maintenance, release, and executive reporting DTOs are available through the
  optional Production application layer.
- Repository integrity, recovery admission, long-running stability contracts,
  release readiness, governance, license, and contribution evidence improve
  controlled operation without modifying Core behavior.

## Production, observability, diagnostics, and reliability

Every v2.5 report is diagnostic-only. It cannot call an Agent, transition a
Page, approve work, generate an image, repair persisted data, contact GitHub,
or make a network probe. The StateMachine remains authoritative for the
one-page workflow.

## Release and OSS readiness

The RC includes local release checklist, artifact, version, documentation,
migration, governance, dependency-license, and community readiness validation.
It does not build, sign, upload, tag, or publish artifacts automatically.

## Performance and compatibility

Provider-free benchmark smoke covers workflow, repository, provider/backend
runtime, automation, notification, diagnostics, reporting, health monitoring,
configuration, and release-readiness boundaries. v1.x and v2.0.x-v2.4.x Python
API, CLI, FastAPI DTO, MCP, Workflow, Repository, Plugin, Extension SDK,
Provider, Image Backend, Automation, Notification, Diagnostics, and Health
contracts are retained. See [the compatibility audit](docs/COMPATIBILITY_V2_5_RC1.md).

Python, MCP, optional OpenAPI, and SBOM use `2.5.0rc1`; the npm frontend uses
the equivalent `2.5.0-rc.1` prerelease form.

## Known issues

- Hosted CI, dependency/CVE audit, secret scan, and upload verification must run
  for the exact RC tag before publication.
- Non-mock adapters, cloud monitoring, distributed runtime, and marketplace work
  remain intentionally outside this RC scope.

## Before stable release

1. Accept only corrective RC feedback; do not expand scope.
2. Confirm hosted backend, frontend, docs, package, security, release, nightly,
   benchmark, diagnostics, production, and enterprise CI jobs for the RC tag.
3. Promote reviewed metadata to `2.5.0`, regenerate release assets, and publish
   the approved tag and artifacts.

## GitHub Release body

Use this document as the GitHub prerelease body for tag `v2.5.0rc1` after hosted
checks and publication-time security scans succeed.
