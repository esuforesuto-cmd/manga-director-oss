# Creative Collaboration Foundation

v3.1 adds an Application-layer, read-only collaboration projection. It turns a
single existing Page context into workspace, member, session, review-assignment,
approval-state, activity, and summary DTOs. It is a planning and visibility
surface, not a collaborative editor or workflow controller.

## Safety boundary

- A workspace is scoped to one Page and never persists itself.
- Members describe human roles; they neither construct nor invoke Agents.
- Review assignments are advisory. They do not complete quality review.
- Approval remains `not_ready` or `pending_human_review`; it never grants
  approval or transitions StateMachine state.
- The existing WorkflowEngine and StateMachine remain the only execution and
  transition authorities.

## Delivery

- CLI: `manga-director director collaboration-foundation --project <id> --page <n>`
- FastAPI: `GET /v3.1/collaboration`
- MCP: `collaboration_foundation`

All paths render the same transport-neutral DTO. See the
[example](../examples/creative_collaboration/run.py).
