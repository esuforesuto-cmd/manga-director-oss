# Provider Selection

Provider selection is an Application/Adapter composition concern. Workflow,
Agent, CLI, MCP, and Web UI code must depend on `LLMProvider` and
`LLMFactory`, not a provider name.

## Selection criteria

- Protocol and Factory compatibility with a deterministic Mock fixture.
- Capability and model metadata sufficient for local validation.
- Secret boundary, error behavior, lifecycle health, licensing, and operator
  ownership documented before an implementation Issue is accepted.
- Provider-neutral prompt and Agent behavior preserved.

## Candidate catalog

OpenAI, Anthropic, Gemini, Azure OpenAI, AWS Bedrock, OpenRouter, DeepSeek,
Mistral, Cohere, Groq, Ollama, LM Studio, vLLM, and Llama.cpp are candidates
only. None is approved or implemented by this planning document.

## CI policy

Provider selection, discovery, capability, and lifecycle tests must use mocks.
CI may not send a request, load a credential, or set an availability claim for
an external Provider.

## Advisory runtime selection

v2.6 adds `ProviderOrchestrator`, an Application-layer metadata reader. Its
`ProviderCapabilityMatrix` and `ProviderSelectionReport` score registered
capabilities, then use the runtime's stable priority order as a tie-breaker.
Latency is a low-confidence relative value derived from priority metadata; cost
is explicitly unknown until an approved price source exists. Fallbacks are a
declarative candidate list and are never executed.

This leaves `LLMProvider`, `LLMFactory`, and every Agent unchanged. Use
`manga-director planning provider --capability text` to review the DTO without
creating or invoking a Provider.

## Model Router contract

`ProviderOrchestrator` is the public Model Router. It normalizes requested
capabilities, ranks only registered metadata, and reports no selection when no
provider satisfies the complete request. The report never constructs,
switches, or invokes a Provider; its fallback list is advisory only.

## Optimization analysis

`ProviderOptimizer` extends the advisory surface with a local metadata and
construction-health comparison. It exposes capability, relative latency,
explicitly unknown cost, reliability, recommendation, and explanation DTOs.
It does not select a runtime Provider, call a model, fetch pricing, or execute
a fallback. See [Provider Optimization](PROVIDER_OPTIMIZATION.md).
