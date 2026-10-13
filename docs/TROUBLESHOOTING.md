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

Install the `api` extra and run `manga-director api serve`. The server listens
on `127.0.0.1:8000` only. Keep the Web UI on `http://127.0.0.1:3000` or
`http://localhost:3000`; other browser origins are intentionally rejected.

## A provider appears to do nothing

The OpenAI, ComfyUI, and non-mock LLM implementations are explicit
network-free stubs in this baseline. Use `mock` for deterministic local tests.
