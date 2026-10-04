# manga-director v1.0.0

## Overview

`manga-director` v1.0.0 is a headless, typed workflow engine for managing commercial manga production one page at a time. It provides strict state transitions, stateless agents, Project persistence, a CLI, and replaceable image-generator adapters.

## Highlights

- Forward-only workflow from Draft through explicit human approval
- `WorkflowEngine` and `StateMachine` enforce workflow correctness
- JSON/YAML Project persistence with import/export and restart/resume support
- CLI for project management and page workflow operations
- Registry-based image-generator adapters with a deterministic Mock provider
- Public Python API, examples, typed package support, CI, and contributor documentation

## Installation

```bash
python -m pip install manga-director==1.0.0
```

## Quick Start

```bash
manga-director project create --id demo --title "Demo Manga"
manga-director run demo 1
manga-director approve demo 1 --approved-by editor
```

## Architecture

```text
Director → WorkflowEngine → StateMachine → Agents → ImageGenerator
                         ↓
                   ProjectRepository
```

Workflow rules remain in `WorkflowEngine` and `StateMachine`; agents, adapters, repositories, and the CLI do not duplicate those rules.

## What is next

v2 design candidates include FastAPI, a plugin system, MCP integration, Redis/RabbitMQ/Celery delivery options, database repositories, Web UI, multi-provider controls, batch workflows, and multi-page workflows. These are design items only and are not part of v1.0.0.

For complete details, see [README.md](README.md), [CHANGELOG.md](CHANGELOG.md), and [docs/ROADMAP_v2.md](docs/ROADMAP_v2.md).
