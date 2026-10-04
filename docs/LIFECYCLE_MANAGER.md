# Lifecycle Manager Foundation

## Scope

`LifecycleManager` creates descriptive references for an existing project and
exactly one existing Page. A `LifecycleManagerFoundationReport` links supplied
subject identifiers, source modules, and observed stages; it is not a new
lifecycle state machine.

## Boundaries

Lifecycle references do not persist history, rewrite a record, transition a
Page, enforce retention, archive/delete/restore data, create checkpoints,
retry/recover work, schedule tasks, or publish a release. Existing Project,
Repository, Workflow, and release contracts remain the owner of those actions.

## Workflow safety

The page reference is descriptive and `page_count=1`. All legal transitions
remain delegated to the StateMachine. This foundation cannot bypass a stage,
generate an image without a persisted storyboard, or approve content without a
completed quality review and explicit human approval.
