# Troubleshooting

## `manga-director` is not found

Install the package in the active environment, then run
`python -m manga_director.cli.app --help` or the installed `manga-director`
entry point.

## A workflow command is rejected

Read `manga-director status PROJECT PAGE`. The StateMachine permits only the
next forward state. Create a storyboard before `generate`, complete quality
review before `approve`, and never request multiple pages in one execution.

## A project cannot be loaded

Verify the `config.yaml` repository root and serialization format. Project IDs
are persisted below `projects/` for the local-file adapter. Use `project list`
before attempting an import or deletion.

## PostgreSQL or migration tooling is unavailable

Install the optional extras: `manga-director[postgresql]` for psycopg and
`manga-director[migrations]` for Alembic. SQLite support is part of the base
package through SQLAlchemy.

## The Web UI has no backend response

This repository does not currently ship a FastAPI server. The Web UI tests and
build are supported, but its REST client requires a separately compatible API.
Do not expose it as a production workflow controller without that API boundary.

## A provider appears to do nothing

The OpenAI, ComfyUI, and non-mock LLM implementations are explicit
network-free stubs in this baseline. Use `mock` for deterministic local tests.
