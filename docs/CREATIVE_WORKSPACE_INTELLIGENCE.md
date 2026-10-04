# Creative Workspace Intelligence

`V4IntelligenceService.workspace()` converts an existing Workspace Foundation
projection into activity, timeline, health, and recommendation DTOs. It is a
read-only report: it cannot persist a session or timeline, transition a
workflow, start work, or act on a recommendation.

Use the report to prepare a human review. The authoritative workflow remains
the existing StateMachine, including its one-page execution and storyboard and
quality-review requirements.
