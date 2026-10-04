# Connector SDK

## Design contract

The Connector SDK will define typed, transport-neutral descriptors rather than
an executable plugin interface. A descriptor is expected to declare:

- stable connector identifier and owner;
- supported capabilities and data classes;
- compatibility range and schema references;
- explicit scope and human approval requirements; and
- provenance and audit explanation requirements.

## Compatibility

Connector descriptors are optional and additive. Existing SDK methods, public
API, CLI, FastAPI, MCP, Workflow, Runtime, and Repository contracts remain
unchanged. Dynamic loading, secret management, remote discovery, invocation,
and marketplace distribution are deferred.
