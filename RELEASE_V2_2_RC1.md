# manga-director v2.2.0 RC1

## Overview

v2.2.0rc1 is the release candidate for the v2.2 stable line. It promotes the
reviewed v2.2 performance, runtime, recovery, integrity, health, and
diagnostics improvements without adding a workflow stage or changing a public
contract.

## Improvements

- Large-project repository paths support selective reads, metadata indexing,
  incremental persistence, and optimized database queries behind the existing
  Repository interfaces.
- Batch execution records progress snapshots, checkpoints, statistics, and
  retry summaries while remaining sequential by default.
- Plugin, Extension SDK, configuration, and in-memory event dispatch have
  bounded caches and diagnostic coverage without API changes.

## Performance improvements

Provider-free benchmark smoke and repeatability coverage now cover workflow,
repository, database, batch, plugin, extension, notification, configuration,
and diagnostics boundaries. The retained v2.1 thresholds are regression
guards, not cross-machine performance promises; see
[the benchmark comparison](docs/BENCHMARK_V2_2_RC1.md).

## Reliability improvements

- Workflow recovery preserves the page-engine transition rules.
- Repository integrity and recovery helpers validate saved Project snapshots.
- Health summaries and diagnostic reports expose DTOs, JSON, and Markdown
  views without coupling Core to a presentation runtime.
- Plugin and Extension load failures are isolated and surfaced as typed errors.

## Operational improvements

`diagnostics` and `health` CLI/MCP surfaces report safe summaries. Structured
logging, metrics, tracing, timelines, and audit controls remain observational:
they do not own workflow logic.

## Compatibility

v1.x, v2.0.0, and v2.1.0 public Python imports, CLI commands, local MCP
protocol, Repository contract, Plugin API, Extension SDK, and forward-only
one-page workflow are retained. See
[the v2.2 RC1 compatibility audit](docs/COMPATIBILITY_V2_2_RC1.md).

The Python distribution is `2.2.0rc1`; the independent npm package uses the
equivalent prerelease notation `2.2.0-rc.1`. MCP reads its server version from
the Python package's single version source.

## Known issues and scope

- OpenAI and ComfyUI adapters, and non-mock LLM providers, retain intentional
  API-boundary stubs; this candidate performs no provider network calls.
- FastAPI/OpenAPI and Automation runtimes are not shipped by this source
  baseline. The Web UI is a separately built presentation scaffold and needs a
  compatible external HTTP service.
- Parallel/distributed workflow execution, remote plugin delivery, and cloud
  monitoring remain out of scope.

## Before the stable release

1. Review RC feedback without changing product scope.
2. Run the hosted CI, security, frontend, package, docs, and nightly checks.
3. Promote metadata to `2.2.0`, regenerate release assets, and publish the
   approved tag and artifacts.

## GitHub Release body

Use this document as the release body for the `v2.2.0rc1` prerelease after the
hosted checks for the tagged commit succeed.
