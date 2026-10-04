# Team Workspace

`V60CreativeProductionPlatformFoundationService.team_workspace()` provides an
immutable, project-and-workspace-scoped view of caller-supplied Collaboration
users and assignments. It reports scoped members, role coverage, and whether
the included assignments retain their required review boundary.

The service does not create or persist workspaces, provision users, change
memberships, create assignments, grant approval, or execute collaboration.
Existing Workspace Hub, Collaboration Workspace, Repository interfaces, and
StateMachine authority remain unchanged.
