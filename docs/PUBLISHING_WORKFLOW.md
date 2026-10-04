# Publishing Workflow Intelligence

`V43ProductionIntelligenceService.publishing_workflow()` provides a
planning-only Export Workflow, Publication Profile, Release Schedule,
Distribution Report, and Publishing Summary based on deliverable foundation
evidence. It is a human-review surface, not a publishing integration.

Export workflows never start, exports and artifacts are not created, targets
remain `not_selected`, credentials are not accepted, schedules are not
registered, and distribution/external delivery remains disabled. The report
cannot approve a release or bypass Page quality-review and StateMachine rules.
