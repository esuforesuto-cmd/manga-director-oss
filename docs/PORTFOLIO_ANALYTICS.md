# Portfolio Analytics

`V44EnterpriseIntelligenceService.portfolio_analytics(project_id, context)`
returns immutable metric and risk projections for one caller-supplied portfolio
project. Scores and risk state remain descriptive (`0` and `not_assessed`) until
a separately approved analytics design is adopted.

The report cannot enumerate or persist a portfolio, alter a Project, allocate
capacity, change a schedule, send an alert, remediate risk, or call an external
service.
