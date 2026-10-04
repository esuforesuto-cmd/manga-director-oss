# Creative Governance

Creative Governance validates the visibility of existing workflow guards and
reports creative standards, planning compliance, and audit findings. It is a
presentation-independent DTO service; it does not change Story, Storyboard,
Prompt, image, or review artifacts.

The governance report explicitly retains storyboard, QualityReview, and
HumanApproval checkpoints. It cannot pass quality, approve a Page, or rewrite
the creative plan.

Delivery: `manga-director director creative-governance`, `GET /v3/governance`,
and the `creative_governance` MCP tool.

# v3.5 Governance evidence

v3.5 contributes `CreativePolicyDTO`, `CreativeQualityPolicy`,
`CreativeComplianceReport`, `CreativeAuditReport`, and a Creative Governance
Dashboard. These are advisory audit projections only: they do not edit
creative material, complete quality review, or approve a Page. The domain
StateMachine remains the authority for workflow transitions and an approval
still requires completed quality review.

The same DTO is available through `director creative-governance-v35 --project
<id>`, `GET /v3.5/creative-governance`, and the `creative_governance_v35` MCP
tool.
