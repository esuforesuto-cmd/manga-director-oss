# v5.7 Vision: Manga Production Platform

## Vision update

v5.7 evolves manga-director from a set of production-support reports into a
**Manga Production Platform** design. The platform connects project context,
asset evidence, collaboration, workflow templates, automation plans, and
plugins without replacing the existing workflow or public surfaces.

## Product direction

- **Production Platform:** one project context composes Story, Character, Page,
  Review, and Export evidence for human production teams.
- **Asset Management:** an additive catalog and lifecycle view reuses existing
  Asset DTOs and Repository evidence; it does not create a new repository port.
- **Project Workspace:** a presentation-neutral workspace model groups project,
  page, asset, and review references without owning workflow state.
- **Collaboration Framework:** participants exchange assignments, review
  evidence, and handoffs while human approval remains explicit.
- **Automation Framework:** human-defined templates and rules produce advisory
  plans only; they never dispatch a workflow or approve content.
- **Plugin Ecosystem:** existing manifest, registry, and lifecycle contracts
  remain canonical; future capabilities are opt-in descriptors.

## Non-goals

v5.7 planning does not authorize autonomous execution, automatic approval,
workflow mutation, asset delivery, Cloud services, marketplace publication,
plugin permission escalation, or a Core Architecture rewrite.

## Compatibility commitment

v5.6.0 and all v5.x public Python API, CLI, FastAPI/REST, MCP, Web UI,
Repository, SDK, Plugin, and StateMachine contracts remain supported. New
platform capabilities must be optional and additive.
