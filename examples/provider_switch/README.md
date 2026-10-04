# Provider Switch Planning Example

Configure the default LLM provider through configuration and obtain it through
the existing `LLMFactory`. Agents must not branch on a provider name. Start
with `MockLLM` in CI and follow the acceptance criteria in
[AI Provider Backlog](../../docs/AI_PROVIDERS.md) before adding a provider.
