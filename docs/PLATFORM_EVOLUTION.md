# Platform Evolution: v5.6 to v5.7

v5.7 consolidates existing evidence rather than replacing existing modules.

| Existing capability | v5.7 platform role | Migration rule |
| --- | --- | --- |
| Production Pipeline and Engines | Production evidence providers | Preserve current DTOs and compose their outputs. |
| v3.2 Asset DTOs and reports | Asset evidence providers | Add references only; do not change repository interfaces. |
| Project and Page workflow | Workspace source of truth | Do not duplicate lifecycle state. |
| Review and Approval evidence | Collaboration handoff inputs | Keep human review and approval explicit. |
| Automation plans and rules | Declarative automation inputs | Never execute plans or rules. |
| Plugin manifest, registry, manager | Capability source of truth | Do not replace lifecycle or loading semantics. |

The implementation order is adapter-neutral DTOs first, analysis second, and
governance last. Each step must remain removable by simply omitting new report
calls and metadata.

## Prompt economy

Platform request and report DTOs should carry stable identifiers and references
to already-approved project, asset, workflow, and review evidence. They must
not duplicate story, character, page, or policy content into new prompts. This
keeps the production context compact while preserving a traceable human review
path.
