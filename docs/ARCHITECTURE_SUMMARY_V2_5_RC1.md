# v2.5.0 RC1 Architecture Summary

The established architecture remains unchanged: Domain owns workflow invariants;
the Workflow Engine and StateMachine enforce one-page forward-only execution;
Application services compose ports; Infrastructure implements adapters and
repositories; CLI, FastAPI, MCP, and Web UI are outer delivery adapters.

The v2.5 additions are contained in `manga_director.production`. They compose
existing Quality Automation, Repository Maintenance, Configuration, and
Workflow-context contracts into read-only reports. They do not import a
Presentation adapter, do not modify Domain state, and do not introduce a Core
dependency on delivery, GitHub, network, or publication tooling.

Repository, Provider Runtime, Image Backend Runtime, Plugin, and Extension SDK
boundaries remain port- or protocol-based. The root public Python API has not
been widened; optional reporting APIs stay in the optional Production package.
