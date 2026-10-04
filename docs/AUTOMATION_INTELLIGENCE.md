# Automation Intelligence

## Scope

Automation Intelligence converts a local `AutomationEngineFoundation` preview
into a transparent diagnostic. It reports whether the supplied template, rule,
event, evidence, and human approval boundary are ready to be presented for
review.

## Safety contract

- The result is advisory and `planning_only`.
- It never executes an automation plan or invokes a provider, agent, runtime,
  or workflow.
- It never makes an autonomous decision, learns from an outcome, or approves a
  Page.
- The domain StateMachine remains the sole workflow transition authority.

`AutomationIntelligenceService.preview()` and
`UnifiedSDKFoundation.automation_dashboard()` are additive opt-in APIs.
