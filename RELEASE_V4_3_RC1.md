# manga-director v4.3.0 RC1

## Overview

`v4.3.0rc1` is the release candidate for the additive Creative Production
Platform. It preserves the Core StateMachine, Workflow Engine, Repository
ports, and v4.2 public contracts while adding only human-governed,
non-executing production DTO projections.

## Improvements

- Production Pipeline, Asset Management, Project Workspace, and Deliverable
  Management foundations.
- Production Automation, Asset Intelligence, Publishing Workflow, and Project
  Analytics reports with plan application, export, publication, distribution,
  scheduling, and external service calls disabled.
- Production Governance, Quality Assurance, Operations Monitoring, and Platform
  Reliability reports with enforcement, approval, monitoring, alerting,
  recovery, and remediation disabled.

## Compatibility

This additive prerelease preserves documented v4.2 Python API, CLI, FastAPI,
REST API, MCP, Repository, Workflow, Extension SDK, Plugin, Provider, Backend,
Automation, Notification, and Web UI contracts. No migration is required.

## Known issues

- This is a prerelease; production adoption should wait for stable v4.3.0
  unless prerelease validation is explicitly intended.
- Exact-tag hosted CI, dependency/CVE audit, secret scan, package validation,
  and publication approval remain required before public release.
- Automatic publishing/distribution, commercial integrations, billing, policy
  enforcement, approval automation, monitoring, alerting, recovery, Cloud, and
  distributed runtime remain intentionally out of scope.

## Before v4.3.0

Only corrective, backward-compatible RC feedback will be accepted. No new
workflow, Provider, Backend, external publishing, commercial integration,
Cloud, Marketplace, or distributed-runtime work is planned during
stabilization.

## GitHub Release body

```markdown
## manga-director v4.3.0 RC1

This prerelease validates additive Creative Production Platform foundations and
production intelligence while preserving v4.2 and earlier public contracts.

Please report reproducible RC regressions before the final v4.3.0 release.
```
