# Production Governance for v3.4

Production Governance combines the existing Production Operations and
Optimization observations with policy and compliance DTOs. It reports the
current StateMachine state and an observable bottleneck without operational
authority.

## Safety boundary

The StateMachine remains the only transition authority. This report cannot
enforce a policy, alter the Production Pipeline, start an operation, schedule,
allocate, remediate, execute, generate, approve, configure, or deploy.

## Delivery surfaces

- CLI: `manga-director director production-governance-v34 --project <id>`
- FastAPI: `GET /v3.4/production-governance`
- MCP: `production_governance_v34`

The shared response type is `ProductionGovernanceDashboardDTO`.
