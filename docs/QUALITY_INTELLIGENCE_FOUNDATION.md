# Quality Intelligence Foundation

v3.3 Quality Intelligence projects existing artifact, workflow-history,
storyboard, review, and quality-state evidence into immutable metrics, rules,
findings, dashboard, and summary DTOs. It is analysis and diagnostics only.

Reports never calculate an authoritative quality score, complete a review,
apply remediation, grant approval, or alter workflow state. Quality review and
explicit human approval remain enforced by the existing StateMachine.

Use `manga-director director quality-intelligence-v33 --project <id> --page
<number>`, the optional `/v3.3/quality-intelligence` FastAPI provider, or the
`quality_intelligence_v33` MCP tool.
