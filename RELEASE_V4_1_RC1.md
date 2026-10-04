# manga-director v4.1.0 RC1

## Overview

`v4.1.0rc1` is the release candidate for the additive Creative Agent Platform
cycle. It preserves the Core StateMachine, existing Workflow Engine, Repository
port, and v4.0 public contracts while introducing DTO-only multi-agent planning
and operational evidence.

## Improvements

- Immutable Agent Registry, Profile, Capability, Role, Session, Context, State,
  Request, and Result DTOs.
- One-page Orchestration, Task Planning, Collaboration Workflow, Handoff, and
  Conflict Resolution DTOs with dispatch and execution disabled.
- Human-in-the-Loop, Agent Governance, Observability, and Reliability DTOs with
  approval, enforcement, export, retry, and recovery disabled.

## Compatibility

This additive prerelease preserves documented v4.0 Python API, CLI, FastAPI,
REST API, MCP, Repository, Workflow, Extension SDK, Plugin, Provider, Backend,
Automation, Notification, and Web UI contracts. No migration is required.

## Known issues

- This is a prerelease; production adoption should wait for stable v4.1.0 unless
  prerelease validation is explicitly intended.
- Exact-tag hosted CI, dependency/CVE audit, secret scan, package validation,
  and publication approval remain required before public release.
- Agent execution, remote communication, policy enforcement, telemetry export,
  retry/recovery execution, autonomous AI, Cloud, and distributed runtime remain
  intentionally out of scope.

## Before v4.1.0

Only corrective, backward-compatible RC feedback will be accepted. No new
workflow, Provider, Backend, autonomous agent, Cloud, Marketplace, or
distributed-runtime work is planned during stabilization.

## GitHub Release body

```markdown
## manga-director v4.1.0 RC1

This prerelease validates additive Multi-Agent Registry, Runtime,
Orchestration, Collaboration, Human-in-the-Loop, Governance, Observability,
and Reliability DTOs while preserving documented v4.0 and earlier contracts.

Please report reproducible RC regressions before the final v4.1.0 release.
```
