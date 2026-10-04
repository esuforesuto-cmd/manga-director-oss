# LLM Adapter

## Boundary

`LLMProvider` is the only provider contract used by LLM-assisted agents:

```python
generate(request: PromptRequest) -> LLMResult
```

`PromptRequest` contains `system_prompt`, `user_prompt`, `temperature`, `top_p`, `max_tokens`, and metadata. `LLMResult` records success, content, usage, provider, elapsed time, finish reason, metadata, and messages. `PromptResponse` is the normalized content view exposed by `LLMResult.response`.

No workflow, agent, or CLI command checks a provider name. Provider selection is performed once in the composition root through `LLMFactory`.

## Built-in providers

| Name | Status |
| --- | --- |
| `mock` | Functional deterministic provider for development and tests. |
| `openai` | API-boundary stub; no network request. |
| `anthropic` | API-boundary stub; no network request. |
| `gemini` | API-boundary stub; no network request. |
| `ollama` | API-boundary stub; no network request. |
| `openrouter` | API-boundary stub; no network request. |
| `litellm` | API-boundary stub; no network request. |

Stubs return a typed unsuccessful result with `finish_reason: not_implemented`. They deliberately do not read credentials, make HTTP calls, stream, use vision, or call tools.

## Configuration

Set the selected provider in `config.yaml`:

```yaml
default_llm_provider: mock
```

The CLI composition root creates it through `LLMFactory.create()`, then injects the provider into PageDesign, Editor, Storyboard, Dialogue, and Quality agents. Those agents render `prompts/agent_assist.md` and use the LLM only for advisory assistance; workflow output and state transition validation stay deterministic and owned by `WorkflowEngine` and `StateMachine`.

## Add a provider

Implement the protocol and register a builder during application composition:

```python
from manga_director import LLMProvider, LLMResult, PromptRequest
from manga_director.adapters import LLMFactory


class StudioLLM(LLMProvider):
    def generate(self, request: PromptRequest) -> LLMResult:
        return LLMResult(
            success=True,
            content="Production guidance.",
            usage={},
            provider="studio",
            elapsed_time=0.0,
            finish_reason="stop",
            metadata={},
            messages=[],
        )


LLMFactory.register("studio", StudioLLM)
```

Do not add provider checks to agents, workflows, or CLI commands. A local Plugin may register the same zero-argument builder under `PluginType.LLM`; the CLI composition root applies it to the Factory before reading `default_llm_provider`.

## Prompt templates

LLM instructions are Markdown assets under `src/manga_director/prompts/`. The default `agent_assist.md` receives only `agent_name` and a JSON-serialized page context. A custom `prompt_directory` may provide its own `agent_assist.md`.

Template changes must preserve the single-page, no-skip, explicit-approval invariants stated in `AGENTS.md`.

## Exclusions

This adapter layer does not implement real API communication, credential resolution, streaming, vision, function calling, MCP, or GUI integration.
