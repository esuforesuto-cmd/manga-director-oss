# Story Planner

Story Planner records evidence for an existing Page without generating or
rewriting narrative content. The standard context keys are:

| Key | Required planning evidence |
| --- | --- |
| `story_context` | `premise`, `chapter_goal`, optional `conflict` and `ending_goal`. |
| `world_context` | Established location, rules, organizations, or terminology. |
| `character_context` | Approved character context; motivation is checked separately. |
| `timeline_context` | Ordered scene evidence. |

The planner reports missing evidence rather than inventing a story decision.
It maintains commercial-production continuity by preserving approved context by
reference.
