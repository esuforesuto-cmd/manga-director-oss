# Creative Planning Foundation

`DirectorPlanningService.creative_planning()` produces a read-only plan with
Story, Chapter, Page, Panel, and timeline DTOs. It reads supplied page-design
and storyboard artifacts only; it does not call an image adapter or modify the
Prompt Pipeline.

The report surfaces the existing workflow requirements rather than replacing
them: a storyboard remains persisted before generation, quality remains
required before human approval, and revisions are same-state explicit workflow
actions.

Delivery is available through `manga-director director creative`,
`GET /v3/creative`, and the `creative_planning` MCP tool. Each result sets
`image_generation_invoked` to `false`.

See [Creative Planning example](../examples/creative_planning/run.py).
