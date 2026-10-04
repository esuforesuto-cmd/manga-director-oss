# manga-director v3.3.0 RC1

## Overview

`v3.3.0rc1` is the release candidate for the additive v3.3 release. It keeps
the Core state machine, public interfaces, Repository port, and delivery paths
intact while preparing the Production, Quality, Asset, Project, and Governance
platform DTOs for final release validation.

## Improvements

- Production Pipeline and Intelligence expose one-Page stage, timeline,
  bottleneck, and governance evidence without execution or optimization.
- Quality Intelligence, Analytics, and Governance expose review evidence and
  policy observations without scoring, remediation, or approval authority.
- Asset Lifecycle, Intelligence, and Governance remain redacted,
  Repository-port-only, and cannot retain, archive, delete, repair, or write.
- Project Intelligence, Operations, and Governance provide advisory milestone,
  risk, resource-shape, and delivery evidence without allocation or scheduling.

## Performance and reliability

Provider-free benchmark smoke coverage covers the v3.3 projection paths.
Workflow, Repository, configuration, diagnostics, reporting, health, recovery,
and release-validation boundaries remain unchanged and are rechecked by the RC
suite.

## Compatibility

This additive prerelease preserves documented v1.x, v2.x, v3.0, v3.1, and v3.2
contracts for Python, CLI, FastAPI, MCP, REST, workflows, repositories,
Knowledge/Creative/Asset/Analytics/Review/Diagnostics/Reporting/Governance
APIs, Plugin, Extension SDK, Provider, Image Backend, Automation, Notification,
and Health surfaces. No migration is required.

## Known issues

- This is a prerelease; production adoption should wait for the stable v3.3.0
  release unless RC validation is explicitly desired.
- Tagged hosted CI, dependency/CVE audit, and secret scanning remain mandatory
  publication gates.
- Provider and image-backend integrations require external configuration; RC
  verification uses mocks and provider-free paths only.

## Before v3.3.0

Only corrective RC feedback that preserves public contracts will be accepted.
No new feature, Provider, Backend, workflow, autonomous AI, Cloud, Marketplace,
or distributed-runtime work is planned during stabilization.

## GitHub Release body

```markdown
## manga-director v3.3.0 RC1

This prerelease validates additive Production, Quality, Asset, Project, and
Governance DTO platforms while preserving the documented v1.x through v3.2
public contracts.

Please report reproducible RC regressions before the final v3.3.0 release.
```
