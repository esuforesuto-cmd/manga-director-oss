# Portfolio Governance

`V44EnterpriseGovernanceService.portfolio_governance(project_id, context)`
combines Portfolio Analytics with immutable human-review policy and compliance
DTOs. It is diagnostic-only and scoped to one caller-supplied portfolio project.

It cannot enforce policy, confirm compliance, allocate capacity, change a
schedule, remediate risk, mutate a Project, persist portfolio data, or emit an
alert.
