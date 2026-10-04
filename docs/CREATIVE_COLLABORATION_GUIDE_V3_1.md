# v3.1.0 Creative Collaboration Guide

Creative Collaboration exposes Workspace, Workspace Member, Collaboration
Session, Review Assignment, Approval State, and activity-report DTOs. These
objects make ownership and review evidence visible while preserving human
decision making.

They do not mutate Project data, execute Agents, change a workflow state,
generate an image, or approve a Page. Use them through the existing CLI,
optional FastAPI, MCP, or Web UI delivery seams only as advisory evidence.

Every Page continues to require StateMachine-validated stages, a persisted
storyboard before generation, and a completed quality review before approval.
