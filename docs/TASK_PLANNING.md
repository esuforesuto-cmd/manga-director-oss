# Task Planning Foundation

The planning API converts local agent declarations into bounded
`TaskBreakdownDTO` records for a supplied one-page workflow context. The
priority model always puts human review, workflow legality, and single-page
scope first.

Planning results are advisory. Tasks remain non-executable, no request or
result is persisted, and the service cannot schedule, assign, or execute them.

## Safety boundary

- Planning does not learn, optimize itself, invoke a model, or make autonomous
  decisions.
- Every generated task requires human review.
- Planning cannot alter workflow state, content, artifacts, or repository data.
