# Project Intelligence Foundation

v3.3 Project Intelligence projects existing Project and one-Page workflow
evidence into immutable health, milestone, resource, schedule, risk, report,
and executive-summary DTOs. It is a bounded diagnostic view, not a project
control plane.

The service does not calculate an authoritative health score, allocate
resources, modify a schedule, commit delivery, apply remediation, or execute a
workflow. Its recommendations tell a human to use the existing StateMachine
only after the required evidence exists.

Use `manga-director director project-intelligence-v33 --project <id> --page
<number>`, the optional `/v3.3/project-intelligence` FastAPI provider, or the
`project_intelligence_v33` MCP tool.
