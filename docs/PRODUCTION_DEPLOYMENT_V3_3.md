# v3.3 Production Deployment Guide

Deploy the existing application and repositories using the normal v3.x process.
Run configuration validation, repository integrity checks, health and
diagnostics reports, then perform a human-reviewed one-Page workflow smoke
test. The v3.3 reports are advisory and require no schema, data, or repository
migration.

Before deployment, keep secrets outside reports, configure Providers and image
Backends explicitly, and verify the deployment environment with the release
checklist. Do not treat a governance report as deployment authorization.
