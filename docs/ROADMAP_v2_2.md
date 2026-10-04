# v2.2 Roadmap

v2.2 is an Issue-driven development cycle on the v2.1.x branch. The Core
architecture, forward-only Page StateMachine, one-page execution invariant, and
public v2 contracts remain unchanged.

## Must

| Priority | Initiative | Reason | Expected issues |
| --- | --- | --- | ---: |
| P0 | Reproducible performance baselines and regression gates | Performance work needs measured, repeatable evidence before optimization. | 3 |
| P0 | Large-Project persistence investigation | Establish safe incremental-save and lazy-load contracts without changing the Repository port. | 4 |
| P0 | Compatibility, architecture, and security release gates | Keep v1.x/v2.x workflow and extension contracts safe throughout Issue-driven work. | 3 |

## Should

| Priority | Initiative | Reason | Expected issues |
| --- | --- | --- | ---: |
| P1 | Sequential Batch scheduler profiling | Identify ordering and resume bottlenecks before considering parallel execution. | 2 |
| P1 | Repository and database query profiling | Support larger projects while preserving `ProjectRepository` and Unit of Work boundaries. | 3 |
| P1 | Plugin and Extension SDK ecosystem hardening | Make third-party integrations predictable through compatibility fixtures and documentation. | 3 |
| P1 | Notification delivery operations review | Define observability and retry measurements without adding asynchronous delivery. | 2 |

## Could

| Priority | Initiative | Reason | Expected issues |
| --- | --- | --- | ---: |
| P2 | Repository, prompt, LLM, and image cache designs | Potentially reduce repeated work after hit-rate and invalidation design review. | 4 |
| P2 | Connection-pool configuration design | May improve database operation under load while retaining synchronous SQLAlchemy. | 2 |
| P2 | Provider ecosystem feasibility studies | Assess candidate adapters without adding providers to Core. | 3 |
| P2 | Streaming LLM and async-notification design notes | Capture boundary requirements before any transport or concurrency implementation. | 2 |

## Won't (v2.2)

| Item | Reason |
| --- | --- |
| Breaking Core redesign or StateMachine changes | Violates the v2 compatibility baseline. |
| Marketplace, cloud control plane, microservices, or distributed workflow | Expands the trust and operational boundary beyond this cycle. |
| Actual parallel workflow, async notification, streaming LLM, or remote provider implementation | Requires approved concurrency/network delivery designs and measured prerequisites. |
| FastAPI/OpenAPI or Automation runtime implementation | These remain separately approved product features, not planning-cycle scope. |

## Issue sequencing

1. Create the P0 measurement, compatibility, and persistence-design issues.
2. Attach measured baseline artifacts to every performance proposal.
3. Allow P1/P2 implementation only after its design, compatibility, security,
   test, documentation, and rollback criteria are accepted in the Issue.
