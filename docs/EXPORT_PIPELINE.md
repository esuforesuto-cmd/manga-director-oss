# Export Pipeline

The v5.6 Export Pipeline is an advisory release hand-off for one approved Page.
It requires both the existing `Approved` state and persisted `QualityChecked`
evidence before it reports export eligibility.

The report never creates files, runs an export engine, uploads content, tags a
release, or publishes a page. A human-owned delivery adapter remains responsible
for any actual export after the existing workflow has reached approval.

This boundary preserves existing Export Engine behavior and prevents output from
bypassing storyboard, quality review, or approval requirements.
