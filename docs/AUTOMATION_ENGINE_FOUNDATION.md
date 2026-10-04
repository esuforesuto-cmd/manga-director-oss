# Automation Engine Foundation

## Scope

The v5.2 Automation Engine is an additive, local planning service. It combines a
caller-supplied workflow template, rule, and event into an advisory plan. It
never starts, schedules, routes, persists, retries, dispatches, approves, or
mutates a workflow.

## Safety contract

- Each `WorkflowTemplateDTO` has `page_count=1`; multiple-page requests are not
  representable by this contract.
- A plan is eligible only when evidence, page reference, and an explicit human
  approval boundary are present.
- The domain StateMachine remains the sole transition authority.
- `AutomationPlanDTO` records `execution_requested=False`,
  `execution_performed=False`, and `workflow_mutated=False`.
- A quality-review evidence key can be required by a template or rule; this
  foundation cannot approve a Page.

## SDK use

Use the public Automation Engine boundary for a local, human-gated preview:

```python
from manga_director.platform import AutomationEngineFoundation, AutomationRequestDTO

report = AutomationEngineFoundation().preview(
    AutomationRequestDTO(template_id="template", rule_id="rule", event_id="event")
)
```

`UnifiedSDKFoundation.automation_preview()` is an opt-in, typed facade over the
same local preview. Existing SDK, CLI, FastAPI, MCP, Web UI, repository, and
workflow contracts are unchanged.

## Non-goals

No runtime execution, agent/provider invocation, event delivery, background
task, dynamic loading, persistence, Cloud feature, or automatic decision is
implemented.
