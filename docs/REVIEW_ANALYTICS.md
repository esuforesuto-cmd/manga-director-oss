# Review Analytics

Review Analytics counts supplied, matching, and completed quality reviews for
the one Page declared by `QualityScopeDTO`. It recommends retention or
completion of evidence and never invokes a reviewer, persists review data, or
approves a Page.

The existing StateMachine remains the only authority for an actual approval or
workflow transition. A persisted storyboard and completed quality review remain
mandatory prerequisites.
