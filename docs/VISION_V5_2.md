# v5.2 Vision: Creative Automation Framework

## Vision

v5.2 designs a **Creative Automation Framework** for safe, rule-guided
automation around the v5.1 Composition Platform. Automation is proposed only
when a human-defined rule, explicit scope, evidence requirements, and approval
boundary are present. v5.2 planning does not implement an automation runtime.

## Mission

Make recurring creative-production checks and coordination opportunities easier
to describe, review, simulate, and govern without transferring decision or
workflow authority from people and the existing StateMachine.

## Principles

1. **Rules are explicit and owned.** No inferred policy or autonomous goal
   selection is permitted.
2. **Plan before action.** Templates, events, and rules first produce a
   reviewable Automation Plan; no plan starts work by itself.
3. **StateMachine authority remains absolute.** One execution means one Page;
   stages cannot be skipped; image generation needs a persisted storyboard; and
   approval needs a completed quality review.
4. **Events are evidence, not commands.** Event metadata cannot dispatch,
   schedule, route, or mutate a workflow.
5. **LTS compatibility first.** v5.0 LTS and v5.1 contracts remain valid with
   no required template, rule, or event adoption.

## Non-goals

- Autonomous AI decisions, automatic workflow execution, or automatic approval.
- Core, StateMachine, WorkflowEngine, Repository, Runtime, or API redesign.
- Dynamic plugins, remote event buses, hosted automation, billing, Cloud SaaS,
  marketplace operation, or distributed runtime.

## Target outcome

v5.2 provides a reviewed, issue-ready design for human-governed automation
metadata. Any future implementation requires equivalence fixtures, workflow
invariant tests, and a separate approval for every execution-capable boundary.
