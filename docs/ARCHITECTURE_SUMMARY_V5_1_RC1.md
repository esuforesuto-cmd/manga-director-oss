# v5.1.0 RC1 Architecture Summary

The RC adds a declarative composition layer above the unchanged v5.0 Unified
Platform. Capability Registry, Feature Packs, Platform Profiles, Solution
Templates, and the Composition Engine consume supplied metadata only. The
operating-quality layer consumes that preview only for governance,
observability, lifecycle, and reliability reports.

No v5.0 owner receives a new dependency on composition metadata. Core,
StateMachine, WorkflowEngine, Repository, Runtime, and existing delivery
surfaces retain their responsibilities and source-of-truth ownership.

See [v5.1 architecture](ARCHITECTURE_V5_1.md),
[Composition Engine Foundation](COMPOSITION_ENGINE_FOUNDATION.md), and
[Composition Governance](COMPOSITION_GOVERNANCE.md).
