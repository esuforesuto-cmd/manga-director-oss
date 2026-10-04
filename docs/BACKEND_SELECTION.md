# Image Backend Selection

Image backend selection is an Adapter composition concern. Workflow, Agent,
CLI, MCP, and Web UI code must depend on `ImageGenerator` and its Factory,
never on backend-specific conditions.

## Selection criteria

- Preserve the image-generator Protocol, Factory registration, deterministic
  Mock result, and persisted-storyboard precondition.
- Document artifact ownership, preset/workflow metadata, capability reporting,
  lifecycle health, licensing, and secret/network policy before implementation.
- Keep image generation to one Page and one approved workflow step at a time.

## Candidate catalog

ComfyUI, AUTOMATIC1111, Forge, Fooocus, InvokeAI, Diffusers, Krita AI, Local
Stable Diffusion, and SD.Next are candidates only. This document does not add
or approve a backend implementation.

## CI policy

Backend discovery, preset, workflow-metadata, and lifecycle tests use mock or
local metadata only. CI must not generate images or contact a backend.
