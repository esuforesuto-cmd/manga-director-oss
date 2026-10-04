# Unified Platform Analytics

## Scope

`V48UnifiedPlatformIntelligenceService.platform_analytics()` composes the
existing v4.8 Unified Platform and Modular Runtime foundation reports into a
transport-neutral analytics DTO. It reports only deterministic descriptor
counts and dependency-direction status for an explicitly supplied project and
one existing Page.

## Output

`UnifiedPlatformAnalyticsReport` exposes the source foundation reports,
`V48PlatformAnalyticsDTO`, and a summary. It does not interpret runtime health
or claim that a service is available; its analysis is limited to static
metadata already supplied by the Foundation.

## API compatibility

The new service is an additive export from `manga_director.production`. It
does not change Python root exports, CLI commands, FastAPI/REST routes, MCP
tools, Web UI behavior, Repository interfaces, or Runtime routing. Existing
consumers do not need to migrate.

## Safety

The report is exactly-one-Page scoped and retains StateMachine authority. It
cannot persist analytics, reconfigure a Runtime, call a service, mutate a
Workflow, skip a stage, generate an image, or approve content.
