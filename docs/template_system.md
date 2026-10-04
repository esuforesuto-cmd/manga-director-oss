# Prompt Template System

## Markdown-only templates

Templates are UTF-8 Markdown files. Built-in templates live in `src/manga_director/prompts/`; a configured `prompt_directory` may override a template by the same direct filename.

The default template is `image_prompt.md`. Supported variables are:

| Variable | Source |
| --- | --- |
| `{page_number}` | `WorkflowContext.page.page_id` or `page_number` |
| `{page_type}` | Page Design |
| `{purpose}` | Page Design |
| `{panels}` | Storyboard panels serialized as JSON |
| `{dialogue}` | Dialogue support artifact serialized as JSON |
| `{character}` | Character metadata serialized as JSON |
| `{world}` | World metadata serialized as JSON |

`{page_type}`, `{purpose}`, and `{panels}` are required by the default validation policy. Unknown placeholders or a missing required placeholder produce `ValidationError` before rendering.

## Loader

`PromptTemplateLoader.load(name)` accepts direct `.md` filenames only. Parent directory traversal and non-Markdown names are rejected. It resolves templates in this order:

1. Explicitly registered template.
2. Configured project `prompt_directory`.
3. Built-in package `prompts/` directory.

Every loaded template receives a content hash and source identifier for prompt auditability.

## Future Plugin templates

A future Prompt Plugin can create `PromptTemplate` and call `PromptTemplateLoader.register(template)` during application composition. The loader already provides this registration boundary; Plugin discovery does not need to be added to PromptAgent or individual pipeline stages.

Template content must preserve the single-page, no-skip, explicit-approval invariants. Templates must not include provider-specific instructions.
