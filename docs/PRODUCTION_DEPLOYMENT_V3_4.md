# v3.4 Production Deployment Guide

Deploy the existing application and repositories using the normal v3.x process.
Before promotion, run configuration validation, repository integrity checks,
health and diagnostics reports, then perform a human-reviewed one-Page
workflow smoke test. v3.4 Knowledge, Operations, Organization, Release, and
Governance reports are advisory and require no schema, data, or Repository
migration.

Keep secrets outside reports, configure Providers and image Backends explicitly,
and use the release checklist to verify the target environment. Governance
reports are not deployment authorization and cannot approve a Page.
