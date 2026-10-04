# Platform Profiles

## Purpose

A Platform Profile is a portable declaration of Feature Packs and capabilities
a team intends to use. It is planning and discovery metadata, never a running
configuration, provider selection, or workflow-routing command.

## Illustrative shape

```yaml
profile_id: local.creative-review
title: Creative Review Profile
compatibility: ">=5.0,<6.0"
feature_packs:
  - creative-planning
capabilities:
  - creative.review-summary
  - knowledge.context
evidence:
  quality_review: required
```

The example is illustrative, not a configuration format or runtime command.

## Candidates

| Profile | Scope | Guardrail |
| --- | --- | --- |
| Creative Studio | Planning, context, review, and quality reports. | No image generation or approval action. |
| Production Operations | Pipeline, assets, deliverables, and health reports. | No publishing or deployment action. |
| Enterprise Oversight | Portfolio, governance, audit, and reliability reports. | No access-control enforcement or telemetry. |
| Developer Integration | API, runtime, SDK, and extension compatibility guidance. | No extension installation or service routing. |

Profiles must support empty and legacy-only compositions. Future adoption is
metadata-only and can be removed without data or workflow rollback.
