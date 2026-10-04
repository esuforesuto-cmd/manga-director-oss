# v2.6 Development Planning Report

## Decision

v2.6 development begins as an Issue-driven planning cycle on the v2.5.x branch.
The Core architecture, public API, StateMachine, Repository port, Provider and
Image Backend protocols, and one-page workflow invariants are fixed.

## Planning outcomes

- Roadmap, milestone taxonomy, AI Workflow, Provider Orchestration, Enterprise
  Operations, Automation Planning, upgrade guidance, example tracks, benchmark
  specifications, quality gates, and technical-debt positions are recorded.
- All v2.6 candidates are advisory, deterministic, mock-friendly, and
  presentation-independent until an accepted Issue authorizes implementation.
- Autonomous AI execution, task dispatch, auto-approval, multi-page generation,
  Cloud SaaS, Marketplace, distributed runtime, and Core redesign are excluded.

## Architecture review

No source code, workflow transition, Provider, Backend, Repository, or public
API was changed. The proposed work is constrained to outer Application,
Operations, Adapter, Quality, and Documentation layers and must not introduce a
reverse dependency into Core.

## Next steps

Create Must Issues first, attach deterministic mock fixtures and acceptance
criteria, then promote only reviewed candidates while compatibility and quality
gates remain green.
