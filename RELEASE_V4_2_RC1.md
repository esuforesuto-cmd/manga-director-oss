# manga-director v4.2.0 RC1

## Overview

`v4.2.0rc1` is the release candidate for the additive Autonomous Creative
System foundation. It preserves the Core StateMachine, existing Workflow
Engine, Repository port, and v4.1 public contracts while adding only
human-governed, non-executing DTO projections.

## Improvements

- Goal, execution-session, checkpoint, supervisor, and long-running-task
  preparation DTOs.
- Goal Management, Adaptive Planning, Pipeline Automation, and Execution
  Recovery DTOs with execution, dispatch, retry, recovery, and mutation
  disabled.
- Human Supervision, Execution Governance, Observability, and Reliability DTOs
  with approval, override, enforcement, monitoring, export, and remediation
  disabled.

## Compatibility

This additive prerelease preserves documented v4.1 Python API, CLI, FastAPI,
REST API, MCP, Repository, Workflow, Extension SDK, Plugin, Provider, Backend,
Automation, Notification, and Web UI contracts. No migration is required.

## Known issues

- This is a prerelease; production adoption should wait for stable v4.2.0
  unless prerelease validation is explicitly intended.
- Exact-tag hosted CI, dependency/CVE audit, secret scan, package validation,
  and publication approval remain required before public release.
- Autonomous execution, automatic approval, persistent checkpoints, policy
  enforcement, telemetry export, retry/recovery execution, Cloud, and
  distributed runtime remain intentionally out of scope.

## Before v4.2.0

Only corrective, backward-compatible RC feedback will be accepted. No new
workflow, Provider, Backend, autonomous feature, Cloud, Marketplace, or
distributed-runtime work is planned during stabilization.

## GitHub Release body

```markdown
## manga-director v4.2.0 RC1

This prerelease validates additive Autonomous Execution, Checkpoint,
Supervisor, Pipeline, Governance, Observability, and Reliability DTOs while
preserving v4.1 and earlier public contracts.

Please report reproducible RC regressions before the final v4.2.0 release.
```
