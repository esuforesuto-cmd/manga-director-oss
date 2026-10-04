# manga-director v3.2.0 RC1

## Overview

`v3.2.0rc1` is the release candidate for the next additive v3.2 release. It
keeps the existing Core state machine, public interfaces, and delivery paths
intact while making the read-only Creative Studio, Asset Intelligence, Workflow
Profiles, and Production Analytics capabilities ready for release validation.

## Improvements

- Creative Studio foundation and Workspace reporting remain DTO-based planning
  and visibility tools.
- Asset Intelligence provides catalog, metadata, relationship, analytics,
  integrity, governance, lifecycle, and risk reporting without changing the
  Repository interface.
- Workflow Profiles and intelligence supply profile, pipeline, efficiency,
  timeline, bottleneck, health, and recommendation reports without executing or
  rewriting workflows.
- Production Analytics, Insights, and operational/release readiness services
  provide analysis only; they do not approve, deploy, or automate changes.

## Production and performance

The release candidate includes provider-free benchmark smoke coverage for the
new planning and reporting paths. Measurements are intended to detect local
regressions, not to promise machine-independent timing. Reliability,
compatibility, package, diagnostics, and security review evidence is collected
in the RC1 audit documents.

## Compatibility and migration

This is an additive prerelease that preserves documented v1.x, v2.x, v3.0, and
v3.1 contracts for Python, CLI, FastAPI, MCP, repositories, workflows, plugin
and Extension SDK boundaries, providers, image backends, automation, and
notifications. No migration is required. See the
[compatibility audit](docs/COMPATIBILITY_V3_2_RC1.md) and
[migration guide](docs/MIGRATION_V3_2_RC1.md).

## Known issues

- This is a prerelease; production adoption should wait for the final v3.2.0
  release unless RC validation is explicitly desired.
- Hosted CI, dependency/CVE, and secret scans must be completed for the exact
  release tag before publishing.
- Provider and image-backend integrations require their configured external
  services; RC verification uses mocks and provider-free smoke paths.

## Before v3.2.0

We will evaluate RC feedback, complete the tagged hosted checks, and publish
only fixes that preserve the documented public contracts. No new features are
planned during this RC stabilization period.

## GitHub Release body

```markdown
## manga-director v3.2.0 RC1

This prerelease validates additive Creative Studio, Asset Intelligence,
Workflow Profiles, and Production Analytics capabilities while preserving the
existing v1.x through v3.1 public contracts.

See the compatibility audit and migration guide for upgrade details. Please
report RC regressions with reproduction steps before the final v3.2.0 release.
```
