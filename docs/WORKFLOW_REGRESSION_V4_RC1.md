# v4.0.0 RC1 Workflow Regression Verification

The RC integration path loads a Project, derives Workspace, Memory, Graph, and
Quality reports, then verifies the existing Review, save/reload, diagnostics,
MCP, and Web UI contracts without a workflow transition or Repository write by
v4 modules.

The StateMachine remains authoritative: one page per execution, no skipped
stage, a persisted storyboard before image generation, and completed quality
review before approval. The v4 modules cannot execute a workflow, generate an
image, complete review, or approve a Page.
