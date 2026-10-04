# Provider Governance

`ProviderGovernance` validates the configured default Provider against local
registry metadata, audits capabilities, summarizes in-memory lifecycle states,
checks protocol-compatible recommendation evidence, and reports risk.

It preserves `LLMProvider` and `LLMFactory` interfaces. Lifecycle health uses
local adapter construction only: no model request, remote health probe, pricing
lookup, registry mutation, fallback execution, or credential use occurs.

```bash
manga-director assurance providers
```

