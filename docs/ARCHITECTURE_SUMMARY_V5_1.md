# v5.1.0 Architecture Summary

v5.1.0 completes the optional Composition Platform above the unchanged v5.0
Unified Platform. The composition layer is directional: it reads supplied
metadata from existing owners, while Core, StateMachine, WorkflowEngine,
Repository, Runtime, and delivery surfaces have no dependency on it.

Registry, Packs, Profiles, Templates, and the Engine are declarative. The
Governance, Observability, Lifecycle, and Reliability services consume a
composition preview only and report no runtime action. The Unified SDK exposes
optional preview methods without replacing a legacy entry point.

See [v5.1 architecture](ARCHITECTURE_V5_1.md) and
[Composable Platform completion](V5_1_PLATFORM_SUMMARY.md).
