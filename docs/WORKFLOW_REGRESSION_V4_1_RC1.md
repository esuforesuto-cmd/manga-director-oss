# v4.1 RC1 Workflow Regression

The RC integration path validates:

`Project → Workspace → Agent Registry → Task Planning → Orchestration →
Collaboration → Human Review → Creative Quality → Save/Reload → Reporting →
MCP → Web UI metadata`.

Every v4.1 stage is an immutable one-page projection. No task is dispatched,
agent is invoked, message is sent, review is completed, approval is granted, or
workflow is transitioned. The existing persisted storyboard and quality-review
requirements remain enforced by the StateMachine.
