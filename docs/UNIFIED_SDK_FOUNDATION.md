# Unified SDK Foundation

`UnifiedSDKFoundation` is an opt-in typed convenience facade for platform and
runtime previews. It delegates to the new read-only gateway and declarative
runtime foundation instead of creating a new execution path.

It cannot alter a Page, transition the StateMachine, generate an image,
approve content, dispatch an Agent, persist data, enforce policy, or interact
with external services. Existing SDK and extension APIs remain supported.

