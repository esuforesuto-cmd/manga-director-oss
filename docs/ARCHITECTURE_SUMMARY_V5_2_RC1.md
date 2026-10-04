# v5.2.0 RC1 Architecture Summary

The RC adds an optional Creative Automation Framework above the unchanged v5.0
LTS and v5.1 platform contracts. Templates, rules, events, and registries
consume caller-supplied local metadata only. Intelligence and operating-quality
services consume an advisory preview only for reporting.

No Core, StateMachine, WorkflowEngine, Repository, Runtime, FastAPI, MCP, CLI,
or Web UI owner receives a new dependency on Automation metadata. Their source
of-truth ownership remains unchanged.

See [v5.2 architecture](ARCHITECTURE_V5_2.md),
[Automation Engine Foundation](AUTOMATION_ENGINE_FOUNDATION.md), and
[Automation Governance](AUTOMATION_GOVERNANCE.md).
