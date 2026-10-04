# Provider Optimization

`ProviderOptimizer` compares registered LLM Provider metadata without changing
the `LLMProvider` Protocol or `LLMFactory`. Its report contains capability
coverage, a priority-derived relative latency estimate, explicitly unknown cost,
local construction health, a recommendation, and a selection explanation.

No model request, remote health probe, pricing lookup, fallback execution, or
Factory mutation occurs. Cost is always marked unknown until a separately
approved pricing source and policy exist. The fallback list stays advisory.

```bash
manga-director analytics providers --capability text
```

This command evaluates the local registry only; it does not select a Provider
for workflow execution.

