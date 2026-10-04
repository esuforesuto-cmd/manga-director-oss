# Production Governance

Production Governance converts existing pipeline evidence into immutable policy,
compliance, audit, and summary DTOs. It observes the current StateMachine
state and may show the existing suggested command, but it cannot enforce a
policy, execute a workflow, alter a pipeline, publish, or authorize approval.

The StateMachine and Workflow Engine remain the only transition authority. Use
`director production-governance-v33`, `GET /v3.3/production-governance`, or
MCP `production_governance_v33` for the same transport-neutral DTO.

# v3.5 Governance evidence

v3.5 exposes `ProductionPolicyDTO`, compliance and audit reports, a Production
Governance Dashboard, and a summary derived from local production analysis.
They never schedule, allocate capacity, mutate a pipeline, remediate, deploy,
or apply an optimization. The existing StateMachine continues to be the sole
transition authority.

Use `director production-governance-v35 --project <id>`,
`GET /v3.5/production-governance`, or the `production_governance_v35` MCP tool
to retrieve the DTO.

## v4.3 Iteration 3 operations foundation

`V43ProductionOperationsService.production_governance()` returns immutable
Production Policy, Workflow Compliance, Approval Matrix, Governance Report, and
Governance Summary DTOs from supplied production evidence. The policy is not
enforced, compliance is not confirmed, and the matrix cannot grant approval.

The report preserves exactly-one-Page scope, StateMachine authority, persisted
storyboard requirements before generation, and completed quality-review
requirements before approval. It cannot alter a workflow, persist audit data,
approve, publish, distribute, or call an external/commercial service.
