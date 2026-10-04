# v2.5 Roadmap

v2.5 is an Issue-driven planning cycle on the v2.4.x development branch. The
v2 Core architecture, public contracts, StateMachine, and one-page workflow
invariants are fixed. A roadmap item is not approval to implement: each item
requires an accepted Issue with compatibility, security, test, documentation,
benchmark, and rollback evidence.

## Must

| ID | Objective | Priority | Background | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V25-PROD-01 | Establish production regression evidence for startup, shutdown, recovery, and explicit approval. | P0 | v2.4 has local DTO controls; sustained repeatable release evidence is the next safety step. | Application, Workflow, Observability, CI | M | Application / Quality | V25-QA-01 |
| V25-QA-01 | Consolidate compatibility, upgrade, architecture, package, and quality-pipeline evidence. | P0 | Release checks must be reproducible before ecosystem work expands. | CI, Documentation, Tests | M | Quality / DX | None |
| V25-OPS-01 | Document production operating, logging, health, recovery, and deployment ownership. | P0 | Operators need a clear boundary between safe diagnostics and state-changing work. | Documentation, Application | S | Production / Documentation | V25-PROD-01 |
| V25-ECO-01 | Preserve Provider and Image Backend contract fixtures with deterministic mocks. | P0 | Ecosystem growth must not leak provider logic into Agents or bypass Factory boundaries. | Adapters, Tests, Plugins | M | Adapters / Quality | V25-QA-01 |

## Should

| ID | Objective | Priority | Background | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V25-REP-01 | Record large-repository, history, recovery, and integrity workload evidence. | P1 | Existing port-preserving helpers need measured limits before optimization. | Repository, Database, Benchmarks | M | Infrastructure / Repository | V25-PROD-01 |
| V25-DIAG-01 | Define diagnostics retention, export, and operator ownership policy. | P1 | Current reports are local and bounded; production governance needs explicit policy. | Observability, Security, Documentation | S | Observability / Security | V25-OPS-01 |
| V25-AUTO-01 | Review Automation and Notification retry/recovery runbooks. | P1 | Failure isolation must stay outside the workflow state machine. | Application, Infrastructure | M | Automation / Notification | V25-PROD-01 |
| V25-CONF-01 | Define configuration upgrade compatibility and rollback validation. | P1 | Profiles and governance exist; upgrades need repeatable operator guidance. | Configuration, Documentation, Tests | S | Configuration / Quality | V25-QA-01 |
| V25-DX-01 | Improve contributor quality automation and benchmark recording workflow. | P1 | Issue evidence should be inexpensive and consistent to produce. | Tooling, CI, Documentation | S | DX / Infrastructure | V25-QA-01 |

## Could

| ID | Objective | Priority | Background | Impact | Estimate | Owner layer | Dependencies |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V25-LLM-01 | Prepare proposal and mock-contract packs for OpenAI, Anthropic, Gemini, Azure OpenAI, AWS Bedrock, and OpenRouter. | P2 | Candidate integrations need licensing, secret, capability, and failure review first. | Adapters, Plugin | L | Adapters / Plugin | V25-ECO-01 |
| V25-LLM-02 | Prepare proposal and mock-contract packs for DeepSeek, Mistral, Cohere, Groq, Ollama, LM Studio, vLLM, and Llama.cpp. | P2 | Local and hosted providers must preserve the existing LLMProvider Protocol. | Adapters, Plugin | L | Adapters / Plugin | V25-ECO-01 |
| V25-IMG-01 | Prepare adapter proposals for ComfyUI, AUTOMATIC1111, Forge, Fooocus, InvokeAI, Diffusers, Krita AI, Local Stable Diffusion, and SD.Next. | P2 | Image backends require artifact, preset, workflow-metadata, and safety contracts before code. | Adapters, Plugin | L | Adapters / Plugin | V25-ECO-01 |
| V25-PERF-01 | Define a provider-free production benchmark corpus. | P2 | Workload baselines are needed before cache, pool, or scheduler work is accepted. | Benchmarks, Repository | M | Benchmarks / Infrastructure | V25-REP-01 |

## Won't (v2.5)

| Item | Reason |
| --- | --- |
| Breaking Core redesign or StateMachine change | Violates existing v2 contracts and workflow safety rules. |
| Cloud SaaS, Marketplace, distributed runtime, or microservices | Requires a separate trust, deployment, and recovery architecture. |
| Live credentials or network calls in CI | Mock-only, deterministic contracts remain mandatory. |
| Automatic multi-page generation or implicit approval | Violates one-page and explicit human-approval invariants. |

## Sequencing

1. Create Must Issues with acceptance, rollback, and compatibility criteria.
2. Establish production, quality, and upgrade evidence using mock/local fixtures.
3. Accept Provider/Backend designs only after contract and security review.
4. Promote Should/Could items only while every required quality gate is green.
