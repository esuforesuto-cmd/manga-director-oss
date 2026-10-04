# Production Workspace v2

`V57ProductionWorkspaceService.project_workspace()` composes the existing
Workspace Manager, Project Manager, and Asset Manager reports. It verifies that
project ID, page reference, and workflow state agree without owning any state.

The report has exactly one Page scope. Project persistence, team assignment,
and workflow transitions remain outside this module.
