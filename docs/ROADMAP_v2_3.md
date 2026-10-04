# v2.3 Roadmap

v2.3 is an Issue-driven development cycle on the v2.2.x development branch.
The Core architecture, public v2 contracts, forward-only Page StateMachine,
and one-page execution invariant are fixed. A roadmap entry authorizes
planning only; implementation needs an accepted Issue.

## Must

| Priority | Initiative | Reason | Expected issues | Estimate |
| --- | --- | --- | ---: | --- |
| P0 | Enterprise configuration, audit, and diagnostics contract review | Larger deployments need documented safe defaults, configuration profiles, and operator evidence before feature work. | 4 | M |
| P0 | Provider and image-backend contract fixtures | Ecosystem work must prove factory isolation, mock behavior, validation, and no Core coupling. | 4 | M |
| P0 | v2 compatibility and release gates | Preserve v1.x–v2.2 public contracts while Issues land incrementally. | 3 | S |
| P0 | Large-scale repository/workflow measurement baseline | Enterprise claims require reproducible data for persistence and sequential execution. | 3 | M |

## Should

| Priority | Initiative | Reason | Expected issues | Estimate |
| --- | --- | --- | ---: | --- |
| P1 | Configuration profile guidance | Operators need repeatable local, team, and production-like profile examples without embedding secrets. | 2 | S |
| P1 | Database operational evidence | SQLite/PostgreSQL query, recovery, and integrity behavior need supported workload evidence. | 3 | M |
| P1 | Notification and audit operations review | Delivery failure, redaction, and traceability need a documented enterprise posture. | 2 | M |
| P1 | Plugin and Extension SDK compatibility matrix | Third-party authors need version, manifest, and failure-isolation fixtures. | 3 | M |

## Could

| Priority | Initiative | Reason | Expected issues | Estimate |
| --- | --- | --- | ---: | --- |
| P2 | Azure OpenAI, Bedrock, Vertex AI, OpenRouter provider proposals | Broadens future choice only after provider-specific licensing, security, and mock contracts pass review. | 4 | L |
| P2 | DeepSeek, Mistral, Cohere, local LLM, vLLM, and LM Studio proposals | Capture local and alternative-provider requirements without changing `LLMProvider`. | 4 | L |
| P2 | ComfyUI workflows and image-backend feasibility studies | Define adapter inputs/outputs and artifact ownership before implementation. | 4 | L |
| P2 | Repository connection/cache design records | Explore measured optimizations while retaining Repository semantics. | 2 | M |

## Won't (v2.3)

| Item | Reason |
| --- | --- |
| Breaking Core redesign or StateMachine change | Violates the v2 compatibility and workflow safety baseline. |
| Marketplace, Cloud SaaS, distributed workflow, or microservices | Expands trust, deployment, and operational boundaries beyond this cycle. |
| Unreviewed live-provider credentials or network calls in CI | Mock contracts and isolated provider reviews are mandatory first. |
| Automatic multi-page generation or approval | Violates the page-at-a-time and human-approval invariants. |

## Sequencing

1. Create P0 Issues, attach compatibility and rollback criteria, and establish
   baselines using only mock/provider-free paths.
2. Review Enterprise and provider design records before approving P1/P2 work.
3. Require architecture, security, contract, documentation, and performance
   evidence on every implementation pull request.
