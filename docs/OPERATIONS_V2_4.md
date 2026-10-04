# v2.4.0 Operations Guide

1. Validate profile, secret sources, and repository availability before startup.
2. Record redacted configuration, startup, health, and runtime diagnostics.
3. Inspect provider/backend inventory and health without contacting external
   services or generating images.
4. Run repository integrity checks before manual resume or recovery decisions.
5. Resume only through Project, Chapter, Batch, or page Workflow APIs.
6. Export redacted diagnostics for incident review and follow local retention
   and access policies.

The operations layer is observational and coordinating only. It cannot bypass
the one-page workflow, StateMachine validation, storyboard requirement, quality
review, or explicit approval rule.
