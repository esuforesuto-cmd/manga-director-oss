# v2 LLM Adapter Design

## Status and port

Phase 12 implements the provider-neutral `LLMProvider` port, `PromptRequest`, `PromptResponse`, `LLMResult`, registry-backed `LLMFactory`, Mock provider, and network-free provider stubs. Provider SDKs and network clients remain absent.

```python
class LLMProvider(Protocol):
    def generate(self, request: PromptRequest) -> LLMResult: ...
```

`PromptRequest` contains system/user prompts, temperature, top-p, max tokens, and metadata. `LLMResult` carries success, content, usage, provider, elapsed time, finish reason, metadata, and messages. It must not expose credentials.

## Provider registry

The LLM factory/registry follows the same registration model as image adapters: `register()`, `create()`, and `available()`. Selection comes from application configuration or an explicit request policy, never a provider `if/else` inside an agent.

Implemented adapter identifiers are:

- OpenAI
- Anthropic
- Google Gemini
- Ollama
- OpenRouter
- LiteLLM

The current implementation exposes only request/response generation. Capability negotiation, vLLM, structured output, tools, vision, and streaming remain future design work.

## Placement and use

The CLI composition root creates an `LLMProvider` through the Factory and injects it into the five LLM-assisted page agents. Domain entities, state machines, repositories, and delivery adapters do not import a provider SDK. LLM assistance remains advisory and subject to deterministic validation and human workflow rules.

## Reliability and governance

- Secrets are resolved at the composition root and injected into provider adapters; they are absent from project artifacts, events, and logs.
- Requests have timeout, cancellation, retry, rate-limit, and spend-budget policies owned outside agents.
- Structured-output validation happens after every response; invalid output is a typed failed result, not best-effort parsed data.
- Logs use request/correlation IDs and redaction. Prompts and responses follow the project retention policy.
- Provider/model/template/policy versions are recorded for reproducibility.

## Compatibility

Network-backed LLM use is opt-in. A configuration without an explicit provider uses the deterministic `mock` adapter. New LLM-backed features must provide either a defined non-LLM path or a clear configuration-time validation error.
