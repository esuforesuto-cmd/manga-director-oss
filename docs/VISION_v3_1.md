# Vision v3.1: Production Collaboration and Evidence

## Vision update

v3.1 advances the v3.0 AI Manga Production OS from a safe planning foundation
toward an operationally useful, human-directed creative system. It makes
longer-term intent, collaboration hand-offs, Knowledge change evidence, and
operational quality visible without granting an AI, Agent, or delivery adapter
authority to execute work.

## Production goals

- Preserve the v3.0 one-Page workflow, StateMachine authority, persisted
  storyboard guard, completed quality-review guard, and explicit approval.
- Make project goals, planning templates, decision history, creative metrics,
  and workflow evidence comparable across a human-reviewed production cycle.
- Keep every proposed capability provider-neutral, repository-port-derived,
  deterministic in mock environments, and safe to expose as a DTO.

## Creative collaboration

Editor, Scenario, Character, Storyboard, Review, and Approval workspaces are
planning views over shared project evidence. A workspace may propose ownership,
handoffs, criteria, and pending decisions; it must not write a Page, invoke an
Agent, pass quality, or approve a Page.

## Knowledge evolution

Knowledge versioning, diff, merge, snapshot, timeline, and analytics are
evidence models over Repository-derived records. A future implementation must
define provenance, ownership, conflict policy, retention, redaction, and human
resolution before any persistence or merge action is admitted.

## Operational excellence

Observability, operational dashboards, quality analytics, release analytics,
project metrics, and workflow metrics are read-only reports. They help people
plan validation and maintenance; they do not start monitoring agents, alter
configuration, contact external services, or automate a release.

## Migration strategy

| Stage | Additive outcome | Compatibility and safety rule |
| --- | --- | --- |
| 0 — protect v3.0 | Freeze public contracts and record baseline fixtures. | No Core, public API, persistence, or workflow semantic change. |
| 1 — planning evidence | Add immutable templates, history, and metric DTO designs. | A recommendation names at most one legal Page step and has no execution handle. |
| 2 — collaboration evidence | Add workspace/hand-off/approval-plan designs. | Existing StateMachine and human approval remain the only authority. |
| 3 — Knowledge evolution | Design version/diff/merge/timeline policy and projections. | Repository remains canonical; no hidden store or implicit write. |
| 4 — operations evidence | Design dashboards and analytics as bounded reports. | No external collector, scheduler, deployment, or release action. |
| 5 — reviewed implementation | Admit small, opt-in Issues after compatibility and rollback review. | Preserve v1.x–v3.0 public behavior and all mandatory workflow guards. |

This vision is a planning commitment, not authorization for autonomous AI,
Cloud SaaS, a marketplace, distributed runtime, or Core redesign.
