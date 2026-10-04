# Image Backend Backlog

Image backends must implement the existing `ImageGenerator` boundary through
the Factory/Registry. Agents supply prompts only and never identify a backend.

| Candidate | Planning focus | Required acceptance evidence |
| --- | --- | --- |
| ComfyUI Workflow | workflow payload and artifact path contract | mock generator, persisted-storyboard proof, error mapping, license/security review |
| AUTOMATIC1111 | local API boundary | mock transport, host validation, timeout and output-path policy |
| Fooocus | local backend capability review | mock generator, configuration profile, artifact ownership policy |
| InvokeAI | workflow/model selection boundary | mock transport, validation, metadata normalization |
| Krita AI | desktop integration feasibility | adapter boundary, user-consent policy, artifact lifecycle review |
| Stable Diffusion WebUI Forge | compatible local API boundary | mock transport, host validation, performance fixture |

No backend implementation, image download, model control, or provider-specific
prompt syntax is introduced by this document. Every accepted Issue must retain
the persisted-storyboard-before-image invariant and the one-page rule.
