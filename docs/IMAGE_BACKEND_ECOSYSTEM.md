# Image Backend Ecosystem Backlog

All candidates must preserve `ImageGenerator`, `ImageGeneratorFactory`, the
persisted-storyboard requirement, one-page generation, and no provider-specific
logic in `ImageAgent`. Listing a backend does not authorize an implementation.

| Candidate | Planned Issue theme | Required design evidence |
| --- | --- | --- |
| ComfyUI | workflow contract | workflow metadata, preset validation, artifact ownership |
| AUTOMATIC1111 / Forge | WebUI boundary | request/result mock, safe URL policy, image artifact contract |
| Fooocus / InvokeAI / Krita AI | application adapter proposal | model/preset capabilities, offline fixture, license review |
| Diffusers / Local Stable Diffusion | local runtime proposal | lifecycle, model storage, reproducible mock and artifact policy |

No backend candidate may bypass storyboard persistence, batch multiple page
generation, alter image workflow state, or add network calls to CI.
