# Release Process

Release validation is read-only and provider-free. Build and publishing actions
remain an explicit maintainer responsibility.

1. Run the quality, reliability, maintenance, release, and OSS readiness reports.
2. Confirm version consistency across the canonical Python source, SBOM, and frontend metadata.
3. Verify package artifacts, typed marker, migration guidance, and documentation links.
4. Run the repository test, lint, type-check, benchmark smoke, package, and optional frontend gates.
5. Review the generated checklist, release notes, SBOM, dependency license report, and migration guidance.

The [Release Validation](RELEASE_VALIDATION.md) contract remains the base
quality check; [OSS Readiness](OSS_READINESS.md) adds governance evidence.
For the stable v2.5 release, use the [v2.5 checklist](RELEASE_CHECKLIST_V2_5.md),
[compatibility verification](COMPATIBILITY_V2_5.md), and
[release-ready report](V2_5_RELEASE_READY_REPORT.md). The corresponding
[quality report](V2_5_QUALITY_REPORT.md) records the local validation evidence.
