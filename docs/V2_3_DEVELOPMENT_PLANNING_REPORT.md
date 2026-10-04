# v2.3 Development Planning Report

## Outcome

v2.3 is ready to begin as an Issue-driven, non-breaking development cycle on
the v2.2.x development branch. No package version, public API, workflow rule,
Provider, Plugin, database, or UI behavior changed during planning.

## Planning assets

| Asset | Purpose |
| --- | --- |
| [Roadmap](ROADMAP_v2_3.md) | Must/Should/Could/Won't priorities, rationale, Issue counts, and estimates. |
| [GitHub plan](GITHUB_V2_3_PLAN.md) | Milestone, taxonomy, initial Epics, labels, and Issue rules. |
| [Enterprise backlog](ENTERPRISE.md) | Configuration, Repository, audit, diagnostics, security, database, Plugin, and SDK candidates. |
| [AI providers](AI_PROVIDERS.md) | Provider candidates and mandatory contract/security evidence. |
| [Image backends](IMAGE_BACKENDS.md) | Backend candidates and invariant-preserving acceptance evidence. |
| [Benchmark backlog](../benchmarks/v2_3_backlog.md) | Planned provider/image/repository/workflow measurements. |
| [Roadmap process](ROADMAP_PROCESS.md) | Proposal-to-implementation lifecycle. |

## Quality and governance

The v2.3 Quality Gates add Enterprise smoke, Provider contract, Image Backend
contract, and Configuration compatibility requirements. They require mock
fixtures and preserve the existing architecture, security, compatibility, and
delivery gates. The Technical Debt register now separates resolved, continuing,
deferred, v3, and Enterprise-target work.

## Scope boundaries

- Factory/Registry and Protocol boundaries remain mandatory for providers and
  image backends.
- No live credentials, network calls, or machine-specific latency targets are
  permitted in default CI.
- FastAPI/OpenAPI and Automation remain unshipped in this baseline and are
  planning topics only.
- Marketplace, Cloud SaaS, distributed workflow, microservices, Core redesign,
  automatic approval, and multi-page generation are outside v2.3.

## Maintainer next steps

1. Create the v2.3 milestone and P0 Issues from the GitHub planning source.
2. Require accepted design and compatibility evidence before code starts.
3. Attach deterministic benchmark and mock-contract results to each Provider,
   Image Backend, Enterprise, or performance Issue.
4. Keep release metadata at `2.2.0` until a separately approved release
   process begins.
