# Workflow Analysis

`WorkflowDependencyAnalyzer` is an Application-layer, read-only analyzer for
exactly one `WorkflowContext`. It combines the existing StateMachine-derived
dependency graph and planning evidence into:

- complexity and bottleneck evidence;
- a remaining linear critical path;
- an advisory workflow score; and
- an optional comparison of two contexts.

It never calls `WorkflowEngine`, executes an Agent, changes a Page state,
persists a Project, schedules work, or merges the compared contexts. The
critical path describes only the legal forward workflow already owned by the
StateMachine.

Use `manga-director analytics workflow PROJECT PAGE` to inspect one persisted
Page. The command is analysis-only and leaves the page unchanged.

