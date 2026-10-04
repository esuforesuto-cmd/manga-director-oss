# Performance Baseline v5.7

## Measured scope

The local baseline measures `V57ProductionOrchestrator.production_platform` for
one approved page with persisted storyboard, completed quality review, export
metadata, one template, one Plugin descriptor, and one observed event.

## Result

500 read-only Production Platform projections completed in `0.087163s` on the
local RC verification environment. The measurement creates no asset, event,
task, snapshot, export, repository write, or workflow transition.

## Interpretation

v5.7 is the first Platform-level projection, so no like-for-like v5.6 Platform
baseline exists. This result freezes a v5.7 smoke baseline; existing production
workflow regression contracts remain the compatibility guard.
