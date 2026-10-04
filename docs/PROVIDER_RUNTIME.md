# Provider Runtime

`LLMProvider` remains a single-method Protocol: `generate(request) -> LLMResult`.
The additive `LLMProviderRuntime` observes registered Factory metadata without
calling `generate`.

It provides deterministic discovery, priority ordering, model/alias resolution,
capability and model reports, local construction health, and JSON/Markdown
diagnostics. Provider priority is discovery metadata only. `ProviderFallbackPolicy`
is declarative and disabled by default; no fallback executor is implemented.

Register optional metadata with `LLMFactory.register(name, builder, metadata)`.
Existing two-argument registrations remain compatible and receive safe default
metadata. Provider health validates local adapter construction only; it is not
a network or credential probe.

```python
from manga_director.adapters import LLMProviderRuntime

policy = LLMProviderRuntime().fallback_simulation()
```

`fallback_simulation()` reports a declarative order only. It never invokes a
provider, switches a provider, transmits a request, or changes workflow state.
