# Vision v3: Manga Production OS

## Project vision

`manga-director` v3 is a deliberate evolution from a workflow manager into a
**manga production OS**: a human-directed operating model that makes the
creative intent, production evidence, review decisions, and reusable project
knowledge visible across a manga project. It is not an image-generation
product and it does not replace editorial judgment.

The v3 platform helps a team understand *what may be done next*, *why it is a
good option*, and *which project evidence supports it*. A person remains the
only authority that chooses an action and invokes the existing workflow.

## Mission

Provide an explainable, portable, and safe planning foundation for commercial
manga production while preserving the v2 one-page workflow contract.

## Design principles

1. **Human authority is explicit.** Plans, recommendations, and simulations
   never execute work, approve a Page, or make a paid provider request.
2. **The v2 Core stays authoritative.** `StateMachine` remains the source of
   truth for every Page transition; `WorkflowEngine` remains the only runtime
   that invokes an Agent.
3. **One Page is the execution boundary.** A planning view may describe a
   project, but an execution recommendation identifies at most one legal Page
   step. It never batches or generates multiple Pages.
4. **Knowledge is evidence, not hidden reasoning.** Knowledge projections are
   bounded, attributable, redactable, and obtained through repository ports.
5. **Extensions use stable seams.** New capabilities are additive application
   services, DTOs, registries, and documented contracts; they do not require a
   Core rewrite or provider-specific branching.
6. **Safe by default.** Local, deterministic fixtures are sufficient for
   planning, tests, diagnostics, and benchmarks. Credentials, secrets, and
   internal exception details do not enter reports.
7. **Progress is staged and reversible.** Each v3 Issue has an acceptance
   contract, compatibility proof, documentation, and rollback/removal plan.

## Non-goals

v3 planning explicitly excludes:

- autonomous AI decision making, task dispatch, workflow execution, approval,
  or multi-page generation;
- automatic LLM billing, live-provider calls as a prerequisite for planning,
  or hidden provider fallback execution;
- Cloud SaaS, a marketplace, distributed runtime, microservices, and remote
  agent control;
- changing the v2 Core, `StateMachine`, Page workflow, repository port, or
  public v1/v2 contracts;
- replacing human editorial, legal, or creative review.

## Long-term architecture

The target is an additive architecture around the existing Core:

```text
Presentation adapters (CLI / FastAPI / MCP / Web UI)
                    |
        v3 application DTO and report services
                    |
 Director | Planning | Knowledge | Creative | Review | Memory
                    |
        Existing public ports and compatibility adapters
                    |
 v2 Core: Domain / StateMachine / WorkflowEngine / Repository contracts
```

The layers propose, analyse, and render. They do not invert this dependency or
acquire execution authority. See [v3 Architecture](ARCHITECTURE_V3.md) for the
layer contracts.

## Migration strategy

| Stage | Additive outcome | Compatibility rule |
| --- | --- | --- |
| 0 — protect baseline | Freeze v2.7 public behavior and record contract fixtures. | No version or API change in this planning cycle. |
| 1 — Director Platform | Add planning, decision-trace, and readiness DTO designs. | `Director` remains a coordinator; only `WorkflowEngine` executes. |
| 2 — Knowledge projections | Define read-only indexes, snapshots, and evidence reports through repository ports. | Existing Project persistence remains the canonical record. |
| 3 — Creative pipeline planning | Model creative hand-offs and review checkpoints as plans. | A Page still advances only through the existing StateMachine. |
| 4 — multi-agent collaboration | Define capability, review, and coordinator contracts for proposed Agents. | Agents do not call one another or dispatch work. |
| 5 — separately approved implementation | Implement small opt-in Issues after quality, security, and compatibility evidence. | Every implementation preserves v1–v2.7 imports and behavior. |

This document is a design commitment, not an execution authorization.
