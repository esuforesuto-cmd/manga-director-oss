# Approval Compliance

Approval Compliance makes manual approval prerequisites auditable as immutable
DTOs. It is not an approval endpoint and has no authority to change state.

## Required prerequisites

- domain StateMachine authority;
- a persisted storyboard;
- a completed quality review; and
- a human approval decision.

## Boundary

The report cannot authenticate or authorize a user, grant access, enforce a
policy, submit or grant an approval, issue an override, or transition a
workflow. All verification fields start unconfirmed.
