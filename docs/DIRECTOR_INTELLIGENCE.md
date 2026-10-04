# Director Intelligence

Director Intelligence turns an existing Director session and Creative Planning
report into a Creative Decision Analysis, Planning Comparison, Alternative
Planning Report, Creative Risk Analysis, Creative Recommendation, and Director
Intelligence Summary.

It compares `state_machine_next_step` with human review, reports risk factors,
and recommends review of existing evidence. It cannot select an alternative,
run an Agent, change workflow state, invoke a Provider, or generate an image.

Delivery: `manga-director director creative-intelligence`, `GET
/v3/director-intelligence`, and the `director_intelligence` MCP tool.
