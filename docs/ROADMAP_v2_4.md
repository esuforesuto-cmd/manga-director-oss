# v2.4 Roadmap

v2.4 is an Issue-driven development cycle on the v2.3.x development branch.
The Core architecture, public v2 contracts, StateMachine, and one-page
workflow invariants are fixed. A roadmap entry is planning only; code requires
an accepted Issue with compatibility, security, test, documentation, benchmark,
and rollback evidence.

## Must

| Priority | Initiative | Reason | Expected issues | Estimate | Owner layer |
| --- | --- | --- | ---: | --- | --- |
| P0 | Production operating baseline | Production use needs documented recovery, repository, configuration, logging, and health runbooks before broader integrations. | 5 | M | Application / Infrastructure / Documentation |
| P0 | Observability contract hardening | Health, diagnostics, timelines, metrics, and safe exports need stable DTO and mock-only smoke evidence. | 4 | M | Observability / Application |
| P0 | Provider and backend compatibility fixtures | Ecosystem growth must retain Protocol/Factory isolation, secret safety, and provider-neutral Agents. | 5 | M | Adapters / Tests |
| P0 | v2.3 compatibility and release gates | Every change must preserve Python, CLI, MCP, Repository, Plugin, SDK, Provider, and Backend contracts. | 3 | S | Quality / CI |

## Should

| Priority | Initiative | Reason | Expected issues | Estimate | Owner layer |
| --- | --- | --- | ---: | --- | --- |
| P1 | PostgreSQL production workload evidence | Existing support needs reproducible query, recovery, integrity, and connection-operation data. | 3 | M | Infrastructure / Repository |
| P1 | Configuration migration guidance | Schema evolution needs explicit compatibility checks, dry-run evidence, and rollback documentation. | 2 | S | Configuration / Documentation |
| P1 | Notification and Automation operations review | Retry, audit, failure isolation, and recovery need operating criteria without changing workflow semantics. | 3 | M | Application / Infrastructure |
| P1 | Developer productivity automation | Faster local verification, benchmark recording, and contributor feedback reduce integration risk. | 3 | S | DX / CI |

## Could

| Priority | Initiative | Reason | Expected issues | Estimate | Owner layer |
| --- | --- | --- | ---: | --- | --- |
| P2 | OpenAI Responses, Anthropic Messages, Gemini, Azure OpenAI, Bedrock, and OpenRouter proposals | Candidate LLM integrations require provider-specific contract, licensing, and mock design before implementation. | 6 | L | Adapters / Plugin |
| P2 | DeepSeek, Mistral, Cohere, Groq, Ollama, LM Studio, and vLLM proposals | Capture cloud/local provider requirements without changing `LLMProvider`. | 7 | L | Adapters / Plugin |
| P2 | ComfyUI, AUTOMATIC1111, Forge, Fooocus, InvokeAI, Krita AI, Diffusers, and local SD studies | Define image artifact, workflow metadata, preset, and safety contracts before adapter work. | 8 | L | Adapters / Plugin |
| P2 | Production benchmark corpus | Define large-project fixtures and provider-free workload recordings for later performance Issues. | 2 | M | Benchmarks / Repository |

## Won't (v2.4)

| Item | Reason |
| --- | --- |
| Breaking Core redesign or StateMachine change | Violates established v2 contracts and workflow safety rules. |
| Marketplace, Cloud SaaS, distributed workflow, or microservices | Requires new trust, deployment, and recovery architecture. |
| Live credentials or network calls in CI | Mock-only contracts and isolated provider verification remain mandatory. |
| Automatic multi-page generation or implicit approval | Violates one-page and human-approval invariants. |

## Sequencing

1. Create Must Issues with explicit acceptance and rollback criteria.
2. Establish production and observability evidence using mock/local fixtures.
3. Accept provider/backend designs only after contract review.
4. Promote Should/Could work only when compatibility and quality gates remain green.
