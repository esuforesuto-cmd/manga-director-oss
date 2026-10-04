# Collaboration Foundation

Collaboration DTOs describe a shared one-page context, a planned task, a
non-accepted assignment, and a pending human review. They provide a stable
presentation-neutral shape for future collaboration surfaces without changing
the workflow engine.

`V41AgentFoundationService.collaboration()` returns a `CollaborationReport`.
It has exactly one task for the supplied page, no persisted assignment, no
automatic action, and no completed or approved review.

## Safety boundary

- No task is dispatched or scheduled.
- No assignment is accepted, persisted, or executed.
- No review is completed and no approval is granted.
- Multi-page requests are not represented; each report is scoped to one page.
