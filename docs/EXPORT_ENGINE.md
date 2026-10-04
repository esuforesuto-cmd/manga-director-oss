# Export Engine v1

Export Engine v1 assesses delivery readiness for exactly one approved manga
Page. It provides read-only evidence for print, web, and eBook delivery,
asset packaging, publishing metadata, release bundles, and archives.

It does not create files, generate metadata, assemble an archive, publish
content, upload assets, approve a Page, or change workflow state.

## Eligibility

The report requires existing generated-artifact evidence, completed quality
review evidence, and human approval before an export target can be eligible.
The domain `StateMachine` and existing workflow remain the authority for those
prerequisites.

## Delivery checks

1. Confirm print, web, and eBook target specifications.
2. Confirm generated asset and packaging evidence.
3. Confirm title, language, and rights metadata evidence.
4. Assess release-bundle and archive-integrity eligibility.

`V56ExportEngineService.export_engine()` returns an immutable readiness report
only. Actual delivery remains an approved external process, and existing API,
repository, workflow, CLI, FastAPI, MCP, and Web UI contracts are unchanged.
