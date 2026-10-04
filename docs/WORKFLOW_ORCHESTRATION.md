# Workflow Orchestration

Workflow Orchestration in v2.7 is an Application-layer analysis boundary. It
can model task dependencies, strategy alternatives, complexity, checkpoints,
decision traces, and an execution preview for one Page. It does not alter the
existing Project, Chapter, Batch, or Page engines.

The result must derive the next action from the StateMachine, preserve
persisted-storyboard and quality-review requirements, expose human decision
points, and remain JSON/Markdown DTO data. Orchestration must not invoke an
Agent directly or cause execution.
