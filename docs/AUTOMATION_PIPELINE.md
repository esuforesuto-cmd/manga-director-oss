# Automation Pipeline

The Automation Pipeline combines existing template, rule, event, and evidence
references into an eligibility report. It requires explicit human approval and
records no execution request or dispatch.

Existing Automation Engine, Rule Engine, Event Bus, and Workflow Engine
contracts remain unchanged.

## Public boundary

Use `V57ProductionOrchestrator.automation_pipeline()` with one supplied
`WorkflowContext`. The public `AutomationPipelineDTO` and
`AutomationPipelineReport` identify template, rule, and evidence references;
they never start a workflow, dispatch an event, or apply an approval.
