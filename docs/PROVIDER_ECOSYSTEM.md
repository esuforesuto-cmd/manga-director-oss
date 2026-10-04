# Provider Ecosystem Backlog

All candidates must preserve `LLMProvider`, `LLMFactory`, provider-neutral
Agents, Markdown templates, secret boundaries, and mock-only CI. Listing a
provider does not authorize an implementation.

| Candidate | Planned Issue theme | Required design evidence |
| --- | --- | --- |
| OpenAI Responses API | responses migration/contract | request/result mapping, safety, mock fixture, migration |
| Anthropic Messages API | messages contract | prompt/result mapping, usage, mock fixture |
| Google Gemini | capability contract | model metadata, validation, mock fixture |
| Azure OpenAI | enterprise endpoint policy | endpoint/secret/configuration design |
| AWS Bedrock | cloud-provider boundary | credentials, regional policy, mock fixture |
| OpenRouter | routing contract | provider/model metadata and fallback policy |
| DeepSeek / Mistral / Cohere / Groq | provider proposal | licensing, privacy, model/result fixture |
| Ollama / LM Studio / vLLM | local runtime proposal | endpoint lifecycle, model discovery, offline fixture |

No candidate may introduce live credentials, network tests, provider-name
conditionals in Agents, or a Core dependency.
