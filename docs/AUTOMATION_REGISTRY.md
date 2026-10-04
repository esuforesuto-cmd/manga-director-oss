# Automation Registry Foundation

## Purpose

`AutomationRegistryFoundation` is an explicit in-memory registry for
caller-supplied workflow templates and automation rules. Its report makes the
currently available descriptors inspectable without discovering, loading, or
activating anything.

## Governance and compatibility

- Template and rule identifiers are unique and duplicate registration fails.
- The registry records no external discovery and never changes runtime state.
- Descriptors are optional, additive metadata; legacy consumers keep their
  current entry points and behaviour.
- Human review and StateMachine validation remain outside the registry and
  remain mandatory for any real workflow transition.

External marketplaces, extension loading, remote registries, execution
activation, and policy enforcement are deliberately deferred.
