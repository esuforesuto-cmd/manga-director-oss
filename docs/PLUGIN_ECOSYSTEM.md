# Plugin Ecosystem

The v4.5 Plugin Ecosystem is an additive planning model over the existing
Plugin and Extension SDK contracts. A future descriptor may state plugin
identity, supplied capability, compatibility target, provenance, isolation
expectation, lifecycle state, and policy-review outcome.

No v4.5 planning artifact may register, discover, persist, load, execute,
grant permission to, sandbox, collect telemetry from, update, or remove a
plugin or extension. Existing SDK contracts remain canonical.

Any future opt-in implementation requires human provenance review, explicit
consent, compatibility validation, isolation review, a rollback plan, and the
same one-Page and StateMachine safeguards for workflow-related behavior.

## v5.7 Platform Planning Addendum

v5.7 treats the existing plugin manifest, registry, and manager as the sole
capability source. The planned Platform Plane may compose compatibility,
provenance, isolation, and lifecycle evidence into reports, but it does not
replace plugin discovery, loading, registration, enablement, disablement, or
removal behavior. Marketplace publication, remote installation, permission
grants, and plugin execution remain out of scope.
