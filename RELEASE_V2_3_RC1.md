# manga-director v2.3.0 RC1

## Overview

v2.3.0rc1 is the release candidate for the v2.3 stable line. It promotes the
reviewed provider/backend runtime, enterprise configuration, repository
scalability, health, diagnostics, recovery, and reliability work without
adding a workflow stage or changing a public contract.

## Improvements

- Repository indexes, bounded history reads, self-checks, and integrity
  evidence remain optional helpers over the unchanged Repository port.
- Provider and image backend runtimes provide metadata discovery, lifecycle
  health, diagnostics, and no-network validation while preserving their
  factories and protocols.
- Enterprise diagnostics and configuration governance provide redacted,
  transport-neutral JSON/Markdown evidence.
- The optional `api` extra exposes DTO-only observability routes. It is not a
  workflow REST API and does not expose Domain models.

## Enterprise improvements

Read-only configuration profiles, compatibility/integrity/fingerprint checks,
repository scalability helpers, safe health summaries, and diagnostics reports
support controlled large-project operation without adding cloud management or
distributed execution.

## Provider Runtime and Image Backend improvements

Registered adapters retain their factory/registry contracts and can report
`ready`, `healthy`, `degraded`, `unavailable`, and `shutdown` lifecycle state.
Checks construct local stubs only: no provider request or image generation is
performed by health or diagnostics paths.

## Performance and reliability

Provider-free benchmark smoke and repeatability checks cover workflow,
repository, database, provider/backend runtime, notification, automation,
plugin, extension, and batch boundaries. Recovery, integrity, health,
diagnostics, Plugin isolation, and Extension isolation remain covered by the
test suite.

## Compatibility

v1.x, v2.0.x, v2.1.x, and v2.2.x root Python exports, CLI commands, local MCP
protocol, page workflow, Repository contract, Plugin API, Extension SDK,
Provider API, and Image Backend API are retained. See
[the compatibility audit](docs/COMPATIBILITY_V2_3_RC1.md).

The Python distribution is `2.3.0rc1`; the independent npm package uses
`2.3.0-rc.1`. Package version, MCP server metadata, and optional OpenAPI
metadata derive from the Python package version source.

## Known issues and scope

- Non-mock provider/backend adapters remain intentional API-boundary stubs.
- The optional FastAPI adapter exposes observability DTOs only; it is not a
  workflow API or Web UI backend.
- Cloud monitoring, remote provider probes, parallel/distributed execution,
  remote plugin delivery, and marketplace capabilities remain out of scope.

## Before the stable release

1. Accept only corrective RC feedback; do not expand product scope.
2. Confirm hosted backend, frontend, docs, package, security, release, nightly,
   benchmark, diagnostics, and enterprise CI jobs for the RC tag.
3. Promote approved metadata to `2.3.0`, regenerate release assets, then
   publish the reviewed tag and artifacts.

## GitHub Release body

Use this document as the release body for the `v2.3.0rc1` prerelease after
hosted checks for the tagged commit succeed.
