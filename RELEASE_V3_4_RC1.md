# manga-director v3.4.0 RC1

## Overview

`v3.4.0rc1` is the release candidate for the additive v3.4 cycle. It retains
the Core state machine, public interfaces, Repository port, and delivery paths
while preparing Knowledge Platform, Production Operations, Organization
Intelligence, Release Intelligence, and Governance DTOs for final review.

## Improvements

- Knowledge Platform and Intelligence provide bounded catalog, relationship,
  quality, coverage, recommendation, and governance evidence through the
  existing Repository port without writes, remote search, retention, or repair.
- Production Operations, Optimization, and Governance provide one-Page status,
  capacity-shape, bottleneck, policy, and compliance observations without
  execution, allocation, scheduling, remediation, or pipeline changes.
- Organization Intelligence, Analytics, and Governance provide redacted local
  role and collaboration observations without personnel scoring, assignment,
  notification, or delivery commitments.
- Release Intelligence, Analytics, and Governance provide local compatibility
  and release-evidence views without hosted collection, authorization, tagging,
  signing, publication, or deployment.

## Performance and reliability

Provider-free benchmark smoke covers v3.4 Foundation, Intelligence, and
Governance projection paths. Workflow, Repository, recovery, configuration,
diagnostics, reporting, health, and release-validation boundaries are unchanged
and rechecked by the RC suite.

## Compatibility

This additive prerelease preserves documented v1.x, v2.x, v3.0, v3.1, v3.2,
and v3.3 contracts for Python, CLI, FastAPI, REST, MCP, Workflow, Repository,
Knowledge, Creative, Asset, Analytics, Review, Diagnostics, Reporting,
Governance, Operations, Plugin, Extension SDK, Provider, Image Backend,
Automation, Notification, and Health surfaces. No migration is required.

## Known issues

- This is a prerelease; production adoption should wait for stable v3.4.0
  unless RC validation is explicitly desired.
- Tagged hosted CI, dependency/CVE audit, and secret scanning remain mandatory
  publication gates.
- Provider and image-backend integrations require external configuration; RC
  verification uses mocks and provider-free paths only.

## Before v3.4.0

Only corrective RC feedback that preserves public contracts will be accepted.
No new feature, workflow, Provider, Backend, autonomous AI, Cloud, Marketplace,
or distributed-runtime work is planned during stabilization.

## GitHub Release body

```markdown
## manga-director v3.4.0 RC1

This prerelease validates additive Knowledge Platform, Production Operations,
Organization Intelligence, Release Intelligence, and Governance DTOs while
preserving documented v1.x through v3.3 public contracts.

Please report reproducible RC regressions before the final v3.4.0 release.
```
