# v2.2 Development Planning Report

## Decision

The project is ready to transition from the v2.1.0 stable baseline to an
Issue-driven v2.2 development cycle. The package version remains `2.1.0`; this
is planning on the v2.1.x development branch, not a release or a new feature.

## Architecture and compatibility guardrails

- The Domain remains independent; `WorkflowEngine` remains Page-scoped and
  owns only legal one-page state progression and event publication.
- Project, Chapter, and Batch layers continue to delegate to Page workflows;
  no Issue may create multi-page generation or implicit approval.
- Repository, EventBus, ImageGenerator, LLM, Plugin, and Extension SDK remain
  port/registry boundaries. Core does not branch on external providers.
- v1.x and v2.x shipped APIs remain covered by compatibility and release tests.
- FastAPI/OpenAPI and Automation are absent from the baseline. They are
  explicitly out of v2.2 planning scope, not assumed delivery surfaces.

## Planning deliverables

| Area | Result |
| --- | --- |
| Roadmap | [Must/Should/Could/Won't roadmap](ROADMAP_v2_2.md) with priority, rationale, and expected Issue count. |
| GitHub planning | [Milestone and Issue taxonomy](GITHUB_V2_2_PLAN.md), plus local Epic, Performance, Infrastructure, Security, and Maintenance templates. |
| Scalability | [Boundary review](SCALABILITY_REVIEW_V2_2.md) turns Workflow, Repository, Batch, Automation, Notification, Database, Plugin, and SDK bottlenecks into measured Issue directions. |
| Performance | [Measurement guide](PERFORMANCE_GUIDE.md) covers Workflow, Repository, Database, LLM, Image, Notification, Automation, and Plugin boundaries. |
| Ecosystem | [Plugin ecosystem plan](PLUGIN_ECOSYSTEM.md) records provider candidates without adding integrations. |
| Quality | [Quality gates](QUALITY_GATES.md) make architecture, compatibility, security, benchmark smoke, and performance-regression evidence mandatory. |
| Technical debt | [Debt register](TECH_DEBT.md) is organized as resolved, continuing, deferred, and v3 candidates. |

## Example coverage

The examples directory now includes provider-free performance, sequential large
Project planning, SQLite Repository, mock notification/webhook boundary, and
local MCP usage examples. They use existing APIs only and do not introduce
network, concurrency, or workflow behavior.

## External GitHub action

The repository includes import-ready milestone and Issue taxonomy guidance, but
creating a GitHub milestone or Issues requires a maintainer action in the
remote repository. No remote state was changed by this planning phase.

## Next step

Create the P0 Issues from `ROADMAP_v2_2.md`, assign them to the v2.2 milestone,
and require the documented quality evidence before implementation begins.
