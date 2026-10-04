# Solution Template Foundation

`SolutionTemplateDTO` associates an existing Platform Profile with required
evidence and explicit human review. `SolutionTemplateFoundation` validates
only the supplied profile relationship and its advisory safeguards.

Templates are valid only when human review is required and they do not create a
project, start a workflow, or automate approval. A template is thus a reusable
planning shape, never a production automation mechanism.

Where evidence includes workflow material, existing StateMachine validation
remains the sole authority: an execution produces one Page, stages cannot be
skipped, image generation needs a persisted storyboard, and approval needs a
completed quality review.
