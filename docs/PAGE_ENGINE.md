# Page Engine v1

Page Engine v1 defines the Commercial Manga Page Standard for exactly one
existing Page. It reads approved page-design and storyboard evidence to assess
planning, panel layout, camera direction, reader flow, dialogue placement,
scene transition, and impact-panel readiness.

It does not create a name, modify a panel, move a speech balloon, generate
dialogue, invoke image generation, or change the workflow state.

## Standard workflow

1. Verify page purpose, reader emotion, hook, and declared panel count.
2. Verify contiguous storyboard panel order and matching panel roles.
3. Verify camera and focal-composition evidence for each panel.
4. Verify ordered reader flow and dialogue balloon placement.
5. Verify story-aligned scene transition evidence.
6. Verify the big moment, impact panel, and page-turn hook evidence.

`V56PageEngineService.page_engine()` is an immutable, advisory projection that
preserves existing APIs, repository contracts, and StateMachine authority.
