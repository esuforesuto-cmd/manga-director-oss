# Image Backend Runtime

`ImageGenerator` remains a single-method Protocol:
`generate(prompt) -> ImageResult`. `ImageBackendRuntime` observes Factory
metadata without generating an image.

It exposes backend discovery, priority ordering, capability/model/preset
reports, workflow metadata, local construction health, and JSON/Markdown
diagnostics. Backends are still selected through `ImageGeneratorFactory`;
`ImageAgent` never identifies a backend.

Metadata may declare workflow format, capabilities, models, aliases, and
presets. This does not authorize provider-specific prompts, images without a
persisted storyboard, or multi-page generation.
