# Human-in-the-Loop

The current v4.1 Human-in-the-Loop implementation and design are documented in
[Human-in-the-Loop Design](HUMAN_IN_LOOP.md). This compatibility entry point is
provided because the platform documentation uses both filename conventions.

The implementation is DTO-only: approval is never granted, quality review is
never completed, and the StateMachine is never bypassed.
