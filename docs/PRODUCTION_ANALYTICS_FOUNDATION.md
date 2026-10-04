# Production Analytics Foundation

Production Analytics aggregates existing project counts and evidence flags from
one `WorkflowContext`. It reports project, workflow, review, and quality DTOs
without scoring quality, running a review, authorizing approval, or starting
automation.

The report is suited to a presentation adapter or a human operations review;
it is not a release gate and cannot modify the project. Invoke it through
`manga-director director production-analytics --project <id> --page <number>`.

