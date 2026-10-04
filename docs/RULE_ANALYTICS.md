# Rule Analytics

`RuleAnalyticsDTO` makes a single explicit rule's evidence coverage and safety
configuration inspectable. It reports the number of required and supplied
evidence keys, missing requirements, human-review eligibility, and whether the
non-execution safety boundary is preserved.

The analytics layer neither infers nor changes a rule. It cannot enable
execution, self-learning, or automatic approval. A missing evidence requirement
is surfaced for a human to resolve and continues to fail closed.
