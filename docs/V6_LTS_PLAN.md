# v6.x LTS Maintenance Plan

## Scope

v6.x LTS maintains the v6.0 Creative Production Platform without feature
additions. The maintenance baseline covers Platform Core and Kernel, SDK,
Extension Runtime, Marketplace descriptors, Governance, and Observability.

## Operating cadence

1. Run regression and compatibility validation for every maintenance change.
2. Record Platform Health against the v6.0 local baseline.
3. Track SDK and Extension compatibility as additive descriptor surfaces.
4. Certify Marketplace descriptors before an owner performs external
   publication.
5. Triage security advisories and technical debt without changing frozen APIs.

The verified POST-v6.1 I01–I06 readiness work is recorded as additive
pre-release maintenance evidence. It does not promote a v6.1 release, alter the
v6.0 LTS contract, or authorize a subsequent I02 scope.

## Compatibility boundary

v5.x public surfaces remain available. Every workflow execution continues to
process exactly one Page, with StateMachine-owned transitions, a persisted
storyboard before image generation, and completed quality review before
approval.
