# Large Project planning example

This example constructs a Project with Chapters and asks the existing
`ExecutionPlanner` for its persisted sequential order. It does **not** execute
multiple pages at once: every actual queue item still delegates one page to the
Page WorkflowEngine.

Run with `PYTHONPATH=src python examples/large_project/plan.py`.
