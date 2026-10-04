# manga-director v3.0.0

## What's New

v3.0.0 promotes the reviewed RC1 as the first stable AI Manga Production OS
release. It adds no workflow stage, live Provider, Image Backend, autonomous
AI, Cloud service, marketplace, distributed runtime, or breaking public API.

## AI Director Platform

Project and creative goals, planning/execution contexts, Director sessions,
strategies, decision traces, reliability validation, and readiness reports are
read-only Application-layer DTOs. They identify one StateMachine-legal Page
step but never call an Agent, execute a command, transition state, or approve.

## Creative Pipeline

Story, Chapter, Page, and Panel planning plus Creative policy, standards,
governance, compliance, and audit reports expose existing safeguards. They do
not generate images, change an artifact, skip a stage, or weaken storyboard and
quality-before-approval requirements.

## Knowledge Foundation and Creative Knowledge

Knowledge namespaces, categories, tags, references, snapshots, indexes,
Character/World/Story/Scene/Asset projections, relationships, integrity,
governance, quality, and risk reports are repository-derived and redacted. They
preserve the existing Repository port and never create a mutable knowledge store.

## Multi-Agent Foundation and Review Pipeline

Agent profiles, capabilities, assignments, coordination plans, Story and
Storyboard reviews, Character and Knowledge consistency, and Creative Quality
reports are planning and diagnostic DTOs. They cannot instantiate or dispatch
Agents, approve a Page, or alter a workflow result.

## Production and performance improvements

Production readiness, Workflow Intelligence, observability, diagnostics,
reporting, recovery, repository integrity, configuration validation, and health
remain local, advisory evidence. Provider-free benchmark smoke covers planning,
knowledge, director, creative, review, repository, workflow, diagnostics,
reporting, and health boundaries.

## Developer experience

Typed DTOs are available through CLI, FastAPI, MCP, and Web UI delivery seams.
Examples, benchmarks, quality gates, package validation, and frontend checks
remain mock-only and reproducible.

## Compatibility and migration

v3.0.0 is backward compatible with v1.x and v2.0.x-v2.7.x public contracts.
No Project, configuration, workflow, Repository, Plugin, Extension SDK,
Provider, or Image Backend data migration is required. See
[Migration](docs/MIGRATION_V3.md) and [Compatibility](docs/COMPATIBILITY_V3.md).

## Known limitations

Non-mock adapters, autonomous AI, Agent auto-execution, Cloud monitoring,
marketplace, and distributed runtime remain out of scope. All v3 Director,
Creative, Knowledge, Multi-Agent, Review, and readiness services are advisory;
they never auto-execute or auto-approve a Page.

## Roadmap v3.x

Future v3.x work must remain opt-in and retain the one-page StateMachine
authority. Autonomous, Cloud, marketplace, or distributed capability requires a
separately approved architecture, trust, security, compatibility, and
operational model.

## GitHub Release body

Use this document as the GitHub Release body for tag `v3.0.0` after hosted CI,
security scans, and publication checks complete on the release tag.
