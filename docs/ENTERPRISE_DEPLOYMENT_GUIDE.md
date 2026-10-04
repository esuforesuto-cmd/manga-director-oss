# v6.0 Enterprise Deployment Guide

## Supported operating model

Deploy the existing package and its optional v6.0 report services within the
owner's Python, CLI, FastAPI, MCP, and Web UI boundaries. Supply one persisted,
quality-reviewed Page context per workflow execution; retain StateMachine
transition validation as the authority.

## Operational controls

Use Platform Policy and Governance reports as review evidence, and use the
Observability report as a local diagnostic. Configure deployment-specific
identity, access control, secrets, audit retention, network access, signing,
and Marketplace publication outside these read-only DTO services.

## Compatibility and rollback

No v5.x data migration, endpoint migration, CLI migration, Plugin migration,
or workflow migration is required. Stop using optional v6.0 services to roll
back their projections; no v6.0 report persists state.
