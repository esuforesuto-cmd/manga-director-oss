# Rule Engine Foundation

## Purpose

`RuleEngineFoundation` evaluates explicit evidence keys against an
`AutomationRuleDTO`. The result is a deterministic explanation for a human
reviewer, not an instruction to execute work.

## Rule constraints

- Every rule declares an owner and compatible version range.
- Rules are eligible only when all required evidence is supplied.
- `human_review_required` must be true.
- Execution, self-learning, and automatic approval flags must remain false.
- Missing evidence fails closed and is returned in the report.

The engine has no rule inference, rule authoring, state mutation, approval,
provider call, or workflow transition behaviour.

## Compatibility

Rules are optional metadata. They do not replace existing workflow validation
or the StateMachine, so a v5.0 LTS consumer can continue without adopting them.
