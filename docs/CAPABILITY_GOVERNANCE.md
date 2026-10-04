# Capability Governance

`CapabilityGovernanceService` audits declarations already present in a local
Capability Registry: owner module, compatibility range, public-contract flag,
and dynamic-loading flag. It creates a local DTO report only.

The service does not inspect a module's implementation, load an extension,
contact a registry, perform an external audit, or enforce a capability policy.
It preserves the v5.0 LTS rule that module owners retain behavior and
source-of-truth responsibility.
