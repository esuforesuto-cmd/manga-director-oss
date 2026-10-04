# manga-director v2.1.0 RC1

## Overview

v2.1.0 RC1 is a backward-compatible maintenance candidate for the typed,
headless, one-page-at-a-time manga workflow engine. It adds no workflow,
provider, database, UI, or plugin capability.

## Improvements

- Public API, compatibility, architecture, security, and release-operation
  documentation are now explicit and independently testable.
- Python and frontend quality gates are split, cached, and extended with
  package, security, nightly, and release-artifact workflows.
- The Plugin package is explicitly included in built wheels; clean wheel
  installation now verifies CLI, MCP, and Plugin commands.
- MCP server metadata follows the package version and masks unexpected
  transport exceptions.

## Performance and quality

The provider-free benchmark smoke suite passed for Workflow, Repository,
Database, Prompt, LLM, Image, Notification, and Batch planning. The Python
suite passes 120 tests with an 80% coverage gate; the Web UI lint, typecheck,
unit test, and production build pass.

## Compatibility

The documented v2.0 Python API, CLI commands, local MCP DTOs, forward-only
state machine, one-page workflow invariant, explicit human approval, project
persistence, and adapter registry behavior are unchanged. See
[Compatibility Audit](docs/COMPATIBILITY_V2_1_RC1.md).

## Known issues and scope

FastAPI/OpenAPI and Automation are not shipped in this source baseline. The
Web UI remains a tested presentation scaffold whose typed client requires a
separately compatible HTTP service. Real remote providers, distributed workers,
and remote extension delivery are also outside RC1 scope.

## Before v2.1.0 final

1. Review all hosted CI, nightly, package, and security workflow artifacts.
2. Confirm the RC scope gate and known limitations are acceptable for the
   intended release announcement.
3. Publish only an approved final tag after the release checklist is complete.
