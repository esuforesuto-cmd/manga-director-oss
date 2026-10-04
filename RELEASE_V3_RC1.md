# manga-director v3.0.0 RC1

## Overview

`3.0.0rc1` is the first v3 release candidate. It promotes the reviewed,
advisory foundations for the AI Director Platform, Creative Pipeline, Knowledge
Foundation, Multi-Agent Foundation, Review Pipeline, and Production Readiness.
It does not add autonomous AI, Agent dispatch, a Provider or Backend, cloud,
marketplace, distributed runtime, or a breaking public-contract change.

## Highlights

- AI Director sessions, goals, strategies, decision traces, reliability, and
  execution-readiness reports are one-page, StateMachine-derived DTOs.
- Creative plans, governance, policy, compliance, and audit reports expose the
  established storyboard, quality, and human-approval safeguards without
  changing a Page or creative artifact.
- Repository-derived Knowledge and Creative Knowledge projections add bounded,
  redacted indexes, relationships, integrity, governance, quality, and risk
  evidence without changing the Repository port.
- Multi-Agent and Review Pipeline services provide profile, assignment,
  coordination, review, and consistency analysis only; they do not instantiate
  or run Agents.
- CLI, FastAPI, MCP, and Web UI keep their existing delivery roles and render
  transport-neutral DTOs rather than owning workflow rules.

## Production and performance

The RC includes provider-free benchmark smoke for planning, knowledge, director,
review, repository, workflow, diagnostics, reporting, and health boundaries.
Diagnostics, release readiness, integrity, and operational reports are local,
read-only evidence. They do not deploy, schedule, resume, repair, approve, or
authorize a release.

## Compatibility

The v1.x and v2.0.x-v2.7.x Python API, CLI, FastAPI/REST DTO, MCP, Workflow,
Repository, Plugin API, Extension SDK, Provider API, Image Backend API,
Automation, Notification, and Health contracts are retained. Python, MCP,
optional OpenAPI metadata, and the SBOM use `3.0.0rc1`; the npm frontend uses
the valid equivalent `3.0.0-rc.1`.

## Known issues

- Hosted CI, dependency/CVE audit, secret scan, and publication verification
  must run against the exact `v3.0.0rc1` tag before prerelease publication.
- Live providers, autonomous AI, cloud monitoring, distributed execution, and
  marketplace capability remain intentionally outside RC1 scope.

## Before the stable release

1. Accept corrective RC feedback only; do not expand feature scope.
2. Confirm hosted backend, frontend, docs, package, security, release, nightly,
   benchmark, planning, knowledge, director, review, diagnostics, production,
   and enterprise jobs.
3. Promote reviewed metadata to `3.0.0`, regenerate assets, and publish the
   approved tag and artifacts.

## GitHub Release body

Use this document as the GitHub prerelease body for tag `v3.0.0rc1` after the
hosted checks and publication-time security scans succeed.
