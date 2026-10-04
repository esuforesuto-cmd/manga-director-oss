# v3.3.0 RC1 End-to-End Regression Evidence

Local integration and contract suites exercise the established Application-layer
flow: Project -> Story/Chapter/Page/Panel planning -> Production Pipeline ->
Quality Intelligence -> Asset Lifecycle -> Project Intelligence -> Governance
-> explicit Review/Approval -> Save -> Reload -> Resume. Diagnostics,
Reporting, Automation, Notification, FastAPI, MCP, and Web UI stay on their
existing boundaries.

The RC additions are read-only diagnostics. They do not create a second
workflow, skip a stage, generate without a persisted storyboard, approve
without a completed quality review, or accept multiple Page generation.
