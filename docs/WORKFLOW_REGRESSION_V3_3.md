# v3.3.0 Workflow Regression Evidence

Local integration and contract suites exercise the established Application
flow: Project -> Story/Chapter/Page/Panel planning -> Production Pipeline ->
Quality Intelligence -> Asset Lifecycle -> Project Intelligence -> Governance
-> explicit Review/Approval -> Save -> Reload -> Resume. Diagnostics,
Reporting, Automation, Notification, FastAPI, MCP, and Web UI remain on their
existing boundaries.

The v3.3 additions are read-only diagnostics. They do not create another
workflow, skip a stage, generate without a persisted storyboard, approve
without a completed quality review, or accept multiple Page generation.
