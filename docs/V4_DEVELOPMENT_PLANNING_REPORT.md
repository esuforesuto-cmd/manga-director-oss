# manga-director v4.0 Development Planning Report

## Outcome

The v4 planning baseline defines Creative Workspace 2.0, Creative Memory,
Creative Knowledge Graph, and Creative Quality Platform as staged, optional,
human-led DTO projections. No implementation, version change, Core rewrite, or
public-contract change is included.

## Candidate Issue Sequence

1. Establish shared provenance, redaction, and evidence-reference vocabulary.
2. Define Workspace 2.0 projections and deterministic fixture contracts.
3. Define Memory projections by Story, Character, World, Style, and Production.
4. Define typed graph projections and provenance/relationship constraints.
5. Define Creative Quality diagnostic and editorial-review DTO boundaries.
6. Expose only accepted DTOs through additive CLI, FastAPI, MCP, and Web UI
   seams after compatibility review.

## Migration Decision

Existing v3.5 interfaces remain the migration baseline. Every v4 capability
must be additive, opt-in, read-only by default, and rollback-ready. The Core
StateMachine remains the authority for legal transitions, persisted storyboard
requirements, completed quality review, and exactly-one-Page execution.

## Deferred Research

Persistent memory/graph stores, remote search, retention enforcement,
collaboration authority, autonomous creativity, automated quality gates, Cloud
services, marketplace, and distributed runtime require separate architecture
and governance approval.
