# v3.1 Architecture Index

v3.1 keeps [the v3.0 architecture](ARCHITECTURE_SUMMARY_V3.md) authoritative.
[ARCHITECTURE_V3_1.md](ARCHITECTURE_V3_1.md) records the additive planning
responsibilities for Director, Creative, Knowledge, Review, Workflow
Intelligence, Observability, Operations, and Developer Platform services.

All planned services are immutable, transport-neutral, non-executing DTO
composers over existing public ports. They preserve the one-Page StateMachine
workflow and do not change v3.0 Core architecture.

Iteration 1 and Iteration 2 implement this boundary as additive Application
DTO services for collaboration, knowledge evolution and analytics, operations
and operations intelligence, creative review, and developer guidance. See the
[Iteration 2 report](V3_1_ITERATION_2_CREATIVE_REVIEW_REPORT.md).

Iteration 3 adds governance, reliability, readiness, release-quality, and
compatibility diagnostics without widening Core responsibilities. See the
[Iteration 3 report](V3_1_ITERATION_3_RELEASE_QUALITY_REPORT.md).
