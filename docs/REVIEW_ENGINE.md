# Review Engine v1

Review Engine v1 defines the Commercial Manga Review Standard for exactly one
existing Page. It combines supplied story, character, page, storyboard, art,
dialogue, and continuity evidence into a read-only diagnostic report.

It does not execute reviewers, rewrite creative content, create quality
artifacts, approve a Page, or advance the workflow. Human quality review and
approval remain existing workflow responsibilities.

## Standard workflow

1. Review declared story premise and chapter goal evidence.
2. Review character identity and motivation evidence.
3. Review page-design, storyboard, and panel-role evidence.
4. Review visual direction evidence for every panel.
5. Review dialogue placement and voice-style evidence.
6. Review declared continuity differences.
7. Calculate an evidence-coverage score and return minimal revision advice.

`V56ReviewEngineService.review_engine()` is advisory only and preserves existing
review, StateMachine, export, and delivery interfaces.
