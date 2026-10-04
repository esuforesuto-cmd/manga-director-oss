# Unified Platform Dashboard

`UnifiedPlatformDashboardService` combines Context Intelligence, Unified API
Surface, and Unified Runtime Orchestration into a transport-neutral DTO. It
supplies presentation layers with one consistent read-only view while avoiding
a new dashboard persistence or UI ownership layer.

The dashboard cannot collect telemetry, depend on a presentation framework,
persist or publish itself, route services, alter a workflow, dispatch an Agent,
enforce policy, or take an automatic action.

