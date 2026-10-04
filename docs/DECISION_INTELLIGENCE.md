# Decision Intelligence

`V47DecisionIntelligenceService.decision_intelligence()` composes a Decision
Engine Foundation report with immutable analysis and summary DTOs. It expresses
whether supplied evidence coverage, alternatives, risk, and uncertainty have
been assessed; each default remains unassessed until a future caller supplies
evidence.

The report cannot collect/persist evidence, recommend or select a decision,
update a model, decide autonomously, enforce a policy, invoke an Agent, mutate
or execute a workflow, or call an external service.
