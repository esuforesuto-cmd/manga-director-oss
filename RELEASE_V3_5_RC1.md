# manga-director v3.5.0 RC1

## Overview

`v3.5.0rc1` is the release candidate for the additive v3.5 cycle. It retains
the Core StateMachine, Workflow Engine, public interfaces, and Repository port
while making Unified Knowledge Graph, Creative Intelligence, Production
Intelligence, Platform Analytics, and Governance reports available for final
Production Grade OSS review.

## Improvements

- Unified Knowledge Graph projects local node, edge, context, and trace
  evidence through the existing Repository port without graph persistence,
  remote lookup, merge, repair, or retention.
- Creative Intelligence and Analytics provide story, character, Page Quality,
  trend, and recommendation evidence without generation, creative changes,
  review completion, or Page approval.
- Production Intelligence and Optimization provide pipeline, capacity, risk,
  delivery, and executive evidence without scheduling, allocation, workflow
  changes, remediation, or deployment.
- Platform Analytics provides local KPI, history, regression, health, and
  dashboard evidence without collection, monitoring, enforcement, release
  authorization, or external action.
- Governance exposes human-reviewed policy, compliance, audit, and summary
  DTOs without policy enforcement, durable audit persistence, or automation.

## Performance and reliability

Provider-free benchmark smoke covers v3.5 graph, analytics, dashboard,
Repository, and reporting projections. Existing workflow, recovery,
configuration, diagnostics, health, Plugin, Extension SDK, and Repository
validation paths remain unchanged and are rechecked by the RC suite.

## Compatibility

This additive prerelease preserves v3.4 and documented v1.x-v3.3 Python API,
CLI, FastAPI, REST, MCP, Workflow, Repository, Extension SDK, Plugin, Provider,
Backend, Automation, Notification, Health, Diagnostics, Reporting, and Web UI
contracts. No migration is required.

## Known issues

- This is a prerelease; production adoption should wait for stable v3.5.0
  unless RC validation is explicitly intended.
- Exact-tag hosted CI, dependency/CVE audit, secret scanning, and publication
  workflows remain mandatory before public release.
- Provider and image-backend integrations remain externally configured; RC
  validation uses mock and provider-free paths only.

## Before v3.5.0

Only corrective RC feedback that preserves public contracts will be accepted.
No new feature, workflow, Provider, Backend, autonomous AI, Cloud,
Marketplace, or distributed-runtime work is planned during stabilization.

## GitHub Release body

```markdown
## manga-director v3.5.0 RC1

This prerelease validates additive Unified Knowledge Graph, Creative
Intelligence, Production Intelligence, Platform Analytics, and Governance DTOs
while preserving documented v1.x through v3.4 public contracts.

Please report reproducible RC regressions before the final v3.5.0 release.
```
