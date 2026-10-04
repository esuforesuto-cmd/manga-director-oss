# manga-director v4.0.0 RC1

## Overview

`v4.0.0rc1` is the release candidate for the additive v4.0 Creative Operating
System cycle. It preserves the existing Core StateMachine, Workflow Engine,
public interfaces, and Repository port while bringing Creative Workspace,
Creative Memory, Creative Knowledge Graph, Creative Quality, Intelligence, and
Governance projections to final review.

## Improvements

- Creative Workspace provides read-only workspace, session, snapshot, timeline,
  activity, health, recommendation, and governance evidence.
- Creative Memory provides bounded story, character, world, style, and
  production evidence with intelligence and governance reports.
- Creative Knowledge Graph provides Repository-derived node and edge,
  integrity, dependency, analytics, and governance reports.
- Creative Quality provides story, character, visual, editorial, intelligence,
  and governance DTOs that remain human-review-only.

## Compatibility

This additive prerelease preserves the documented v3.5 Python API, CLI,
FastAPI, REST, MCP, Workflow, Repository, Extension SDK, Plugin, Provider,
Backend, Automation, Notification, and Web UI contracts. No migration is
required.

## Known issues

- This prerelease is for RC validation; production adoption should wait for a
  stable v4.0.0 release unless prerelease validation is intended.
- Exact-tag hosted CI, dependency/CVE audit, secret scan, and publication
  approval remain required before public release.
- v4 reports are local, provider-free, and read-only; persistent memory/graph
  stores, policy enforcement, automated remediation, autonomous AI, Cloud, and
  distributed execution are intentionally out of scope.

## Before v4.0.0

Only corrective, backward-compatible RC feedback will be accepted. No new
workflow, Provider, Backend, autonomous AI, Cloud, Marketplace, or distributed
runtime work is planned during stabilization.

## GitHub Release body

```markdown
## manga-director v4.0.0 RC1

This prerelease validates additive Creative Workspace, Creative Memory,
Creative Knowledge Graph, Creative Quality, Intelligence, and Governance DTOs
while preserving documented v3.5 and earlier public contracts.

Please report reproducible RC regressions before the final v4.0.0 release.
```
