# AI Provider Backlog

Candidate providers must implement the existing `LLMProvider` boundary through
the Factory/Registry, never by provider-name branching in Workflow, Agent, or
CLI code. The following are proposals only.

| Candidate | Planning focus | Required acceptance evidence |
| --- | --- | --- |
| Azure OpenAI | enterprise credential and deployment configuration | mock contract, secret isolation, validation, latency fixture, license review |
| AWS Bedrock | regional/model selection and credential boundary | mock contract, IAM/secret design, error mapping, audit policy |
| Vertex AI | project/location configuration | mock contract, configuration validation, error/redaction policy |
| OpenRouter | model-routing behavior | provider-neutral request mapping and rate-limit policy |
| DeepSeek | model capability and licensing review | mock result, metadata normalization, licensing review |
| Mistral | hosted and local deployment boundary | mock result, configuration/secret review |
| Cohere | text-generation mapping | mock result, usage normalization, error mapping |
| Local LLM | offline deployment profile | deterministic mock/fixture, host validation, resource guidance |
| vLLM | local serving protocol boundary | mock transport, timeout/health policy, performance fixture |
| LM Studio | local desktop protocol boundary | mock transport, host validation, configuration example |

No real API communication, streaming, vision, function calling, or credential
is part of this planning artifact. Provider implementations require an accepted
Issue, independent security review, contract test, and documentation.
