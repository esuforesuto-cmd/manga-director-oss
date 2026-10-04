# Lifecycle Management Design

## Purpose

Lifecycle Management supplies a common reference vocabulary for existing
objects and reports. It does not introduce a new state machine, persistence
format, retention service, scheduler, or release operation.

## Reference lifecycles

| Subject | Reference stages | Owning authority |
| --- | --- | --- |
| Project and Page | Existing project/chapter/page lifecycle and legal Page workflow stages. | Existing Project services and StateMachine. |
| Creative artifact | Draft/reference/reviewed/deliverable links. | Existing production and quality services. |
| Knowledge | Captured/indexed/assessed/superseded reference history. | Knowledge repository and its established contracts. |
| Decision | Context/evidence/review-ready/manual outcome reference. | Human owner plus existing Approval/Decision contracts. |
| Production and release | Planned/observed/quality-reviewed/release-ready report references. | Production, operations, and release contracts. |

These stages are descriptive only. They cannot be submitted as commands or
used to transition a Page outside the StateMachine.

## Lifecycle record design

Future lifecycle references should include subject type and stable identifier,
source module, observed-at time, source snapshot/trace identifier, provenance,
freshness, redaction state, human owner where applicable, and a link to the
owning report. They should never copy secret content or claim a completed
action that the owning module has not recorded.

## Retention and recovery boundaries

Retention policies, archival, replay, recovery, and deletion remain owned by
their existing repositories and release procedures. A v4.8 aggregate may
surface whether supplied evidence contains a retention or recovery reference;
it cannot retain, delete, restore, checkpoint, retry, or recover anything.

## Workflow safeguards

Lifecycle views must preserve exactly-one-Page workflow scope. A persisted
storyboard is required before image generation, a completed quality review is
required before approval, and all legal transitions remain delegated to the
StateMachine.
