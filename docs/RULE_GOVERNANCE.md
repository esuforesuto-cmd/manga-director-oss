# Rule Governance

Rule Governance audits the selected caller-supplied rule against an explicit
policy: owner, evidence, human review, no execution, and no automatic approval
must be declared. `RuleGovernanceService` returns evidence only; it cannot edit
a rule, infer a rule, learn from a decision, enforce policy, or grant approval.

Missing evidence remains a human-review finding. Existing Rule Engine behaviour
and v5.0 LTS public contracts are unchanged.
