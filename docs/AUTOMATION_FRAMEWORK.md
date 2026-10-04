# Creative Automation Framework

## Composition model

The Automation Framework assembles human-owned metadata into an advisory plan.
Every planned automation contains a stable rule identifier, owning team,
single-Page scope, input evidence, expected diagnostics, and required human
approval points.

```text
Workflow Template + Event Record + Rule Definitions + Evidence
                              |
                       Automation Plan Preview
                              |
                    Human Review / Existing Workflow
```

## Automation Plan contract

| Field | Required meaning |
| --- | --- |
| `automation_id` | Stable local identifier and named owner. |
| `page_reference` | Exactly one supplied Page; multi-page scope is invalid. |
| `template_id` / `rule_ids` | Reviewed template and human-defined rules. |
| `event_reference` | Supplied provenance; never a delivery instruction. |
| `required_evidence` | Storyboard, review, provenance, or policy references. |
| `approval_boundary` | Named human decision point before any external action. |

## Safety rules

- Missing evidence, an unknown rule, ambiguous ownership, multi-page scope, or
  absent approval boundary is a validation finding, not a repair opportunity.
- Plans cannot call an Agent, Provider, Backend, plugin, repository writer, or
  workflow service.
- A future execution adapter must delegate every transition to the existing
  StateMachine and cannot bypass storyboard or quality-review requirements.

## v5.7 Platform Planning Addendum

v5.7 reuses this framework as the Automation Plane of the planned Production
Platform. Workflow templates, event references, and human-defined rules remain
declarative inputs to an advisory platform report. The existing Automation
Engine, Rule Engine, Event Bus, WorkflowEngine, and StateMachine retain their
current contracts and ownership; v5.7 introduces no dispatcher, scheduler,
automatic approval, or remote execution path.
