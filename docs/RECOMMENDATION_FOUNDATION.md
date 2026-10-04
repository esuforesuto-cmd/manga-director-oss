# Recommendation Foundation

`V47DecisionFoundationService.recommendation()` composes a Decision Engine
Foundation report with an immutable Recommendation DTO and summary. A
recommendation records that rationale, prerequisites, and human review are
required for exactly one page.

It cannot rank by hidden policy, select or accept an option, grant approval,
dispatch action, create a schedule, remediate a finding, mutate a workflow, or
call an external service.
