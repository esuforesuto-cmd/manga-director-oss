# v4.0.0 Workflow Regression Verification

The stable integration path loads a Project, derives Workspace, Memory, Graph,
Quality, Intelligence, and Governance reports, then checks the existing Review,
save/reload, diagnostics, MCP, and Web UI contracts without a workflow
transition or Repository write by v4 modules.

The StateMachine remains authoritative: exactly one page per execution, no
skipped stage, a persisted storyboard before image generation, and completed
quality review before approval. v4 reports cannot execute a workflow, generate
an image, complete review, or approve a Page.
