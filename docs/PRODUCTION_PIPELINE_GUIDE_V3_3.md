# v3.3 Production Pipeline Guide

Production Pipeline DTOs describe the existing stages, transitions, approval
evidence, sessions, timelines, efficiency, bottlenecks, and governance status.
They are useful for inspection and release review but do not execute stages,
select commands, or change the Page state.

The StateMachine remains the only authority for transitions. One workflow
execution produces exactly one Page, generation requires a persisted
storyboard, and approval requires a completed quality review.
