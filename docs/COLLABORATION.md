# Team Collaboration Design

## Goal

Define reviewable collaboration evidence for enterprise creative teams while
keeping the existing Project owner and StateMachine as the operational source
of truth.

## Proposed planning records

- **Team Profile:** human role, capability description, and ownership evidence.
- **Collaboration Context:** a read-only project/page reference, work intent,
  redaction level, and human owner.
- **Handoff Plan:** proposed producer, reviewer, input/output evidence, and
  unmet prerequisites.
- **Review Plan:** required storyboard, quality-review, policy, and decision
  evidence.
- **Decision Trace:** a human-attributed, immutable planning explanation; not a
  durable audit record or an approval.

## Required controls

- No collaborative record may transition a Page, bypass a workflow stage, or
  approve a Page.
- Each workflow-related context represents at most one existing Page.
- A plan may identify missing storyboard or quality-review evidence, but cannot
  create either one.
- Role labels are descriptive only; no permission, membership, assignment, or
  access-control enforcement is introduced.
- Communication, notifications, chat, and external identity integration remain
  out of scope.

## Future implementation gate

Any collaboration implementation requires explicit owner consent, persisted
audit/review design, access-control threat modeling, StateMachine integration
tests, rollback behavior, and preserved CLI/API/MCP/Web UI compatibility.
