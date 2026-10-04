# v3.2 Migration and Upgrade Planning

v3.2 planning starts from the stable v3.1.0 contract. Planning documents,
examples, and benchmark candidates do not require users to change installed
versions, configuration, persisted Projects, databases, plugins, extensions,
providers, image backends, or workflow behavior.

Any later implementation Issue must be additive and opt-in. It must publish a
compatibility fixture, migration/rollback guidance, and a proof that existing
one-Page StateMachine invariants remain unchanged. No candidate may rely on an
automatic migration, implicit asset persistence, or autonomous execution.
