# Production Optimization

v3.4 Iteration 2 provides a one-Page diagnostic view of production efficiency,
capacity shape, resource-allocation boundaries, and the current workflow-stage
bottleneck. It is a planning aid over existing Production Operations evidence.

## Safety boundary

No capacity plan is applied, no resource is allocated or rebalanced, and no
workflow, StateMachine transition, pipeline, schedule, configuration, or
deployment is changed. A bottleneck is an observation only; remediation stays
with the existing human-directed workflow.

## Delivery surfaces

- CLI: `manga-director director production-optimization-v34 --project <id>`
- FastAPI: `GET /v3.4/production-optimization`
- MCP: `production_optimization_v34`

All transports return `ProductionOptimizationDashboardDTO` only.

## v3.5 Iteration 2

v3.5 adds Pipeline Efficiency, Capacity Forecast, Delivery Risk, Production
Optimization, and Executive Dashboard DTOs. They are local one-Page analysis
reports, not a capacity plan or a delivery commitment.

No optimization is applied, no capacity is allocated, no schedule or workflow
is changed, and no remediation or deployment starts.

- CLI: `manga-director director production-analytics-v35 --project <id>`
- FastAPI: `GET /v3.5/production-analytics`
- MCP: `production_analytics_v35`
