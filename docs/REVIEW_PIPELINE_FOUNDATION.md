# Review Pipeline Foundation

`ReviewPipelineFoundation` evaluates caller-supplied `ReviewEvidenceDTO` for a
single Page. It reports whether a persisted storyboard exists and whether a
matching completed quality review is present.

The resulting `eligible_for_human_page_approval` flag is a diagnostic signal,
not approval. Page approval and transition validation remain exclusively in the
existing domain StateMachine. The foundation never invokes a reviewer or writes
review state.
