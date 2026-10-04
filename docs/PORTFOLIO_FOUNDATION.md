# Portfolio Foundation

`V44EnterpriseFoundationService.portfolio(project_id, context)` returns an
immutable, caller-scoped portfolio identity, one supplied Project observation,
and summary. This initial foundation deliberately models one supplied project
to keep the workflow evidence one-Page scoped and does not enumerate projects.

It cannot persist portfolio data, change a Project, complete milestones,
allocate capacity, schedule work, alert, or commit a forecast. Future
multi-project aggregation requires separate access-control, redaction, and
durable-state approval.
