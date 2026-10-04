# v3.2.0 RC1 End-to-End Regression Evidence

Local integration and contract suites exercise the established Application-layer
flow: Project -> Story/Chapter/Page/Panel planning -> Creative Workspace/Review
-> explicit human approval -> Save -> Reload -> Resume. Asset Intelligence,
Workflow Profiles, Production Analytics, Diagnostics, Reporting, Automation,
Notification, FastAPI, MCP, and Web UI seams remain on existing boundaries.

The RC additions are read-only diagnostics. They do not create a second
workflow, skip a stage, generate without a persisted storyboard, approve without
a completed quality review, or accept multiple Page generation.
