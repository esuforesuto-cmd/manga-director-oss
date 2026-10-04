# Automation Planning

Automation planning creates reviewable, non-executing plans for legal workflow
work. Proposed DTOs may identify a single Page, dependencies, prerequisite
evidence, checkpoints, and human decision points.

They must not schedule a task, start a worker, advance a state, invoke an
Agent, select a provider at runtime, generate an image, or approve a Page.
Existing Batch and Workflow engines remain the only execution surfaces, and
they retain exactly-one-page StateMachine validation.

## v2.7 scope

v2.7 adds planning candidates for Automation Planner, Automation Preview,
Automation Policy, Automation Simulation, Automation Recommendation, and
Automation Diagnostics. They are review artifacts only: no candidate may
dispatch a worker, start a schedule, retry a provider, write state, generate an
image, or approve a Page.
