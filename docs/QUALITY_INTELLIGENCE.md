# Quality Intelligence

`QualityIntelligenceService` turns a `QualityEngineReport` into transparent
quality score, finding count, and recommendation DTOs. The score maps declared
status only; it does not infer evidence, edit policy, change a workflow, or
make an approval decision.

The service is available through the additive
`UnifiedSDKFoundation.quality_dashboard()` method. Existing public surfaces
retain their current behavior.
