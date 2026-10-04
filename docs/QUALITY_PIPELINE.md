# Quality Pipeline

`QualityAutomation` is an Application-layer, read-only facade for daily
development, CI evidence, and production readiness review. It returns typed
DTOs and does not execute an Agent, transition a Page, save a Project, call a
Provider, generate an image, or make a network request.

## Validation stages

1. **Repository validation**: aggregate integrity, repository statistics, and
   large-repository summary through the existing `ProjectRepository` port.
2. **Workflow validation**: one-page Context shape, read-only StateMachine
   inspection, persisted storyboard before generated-or-later states, and
   quality evidence before approval.
3. **Configuration validation**: schema compatibility, integrity, and safe
   fingerprint through the existing Configuration Layer.
4. **API compatibility validation**: root public-export contract and version
   source checks.
5. **Documentation validation**: required release assets and local Markdown
   links.
6. **Release artifact validation**: dynamic package version source and SBOM
   version alignment.

`QualityPipelineReport`, `QualityDashboard`, and `ValidationResult` render
JSON or Markdown. Presentation layers may display these DTOs but may not use a
passing report to bypass WorkflowEngine or StateMachine rules.
