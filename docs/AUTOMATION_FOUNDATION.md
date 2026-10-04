# Automation Foundation

`V57ProductionPlatformFoundationService.automation()` composes supplied
template IDs, rule IDs, and evidence-key references into a human-reviewable
Automation Foundation report.

It reuses the existing Automation Engine contract. It does not dispatch an
event, schedule work, invoke an agent or provider, execute a rule, mutate a
workflow, or approve a Page. Human approval remains required.

## Compatibility

The foundation is opt-in and does not alter existing templates, rules, event
records, automation registries, or workflow behavior.
