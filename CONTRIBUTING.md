# Contributing

Thanks for contributing to manga-director. v6.x is an LTS maintenance line:
contributions should improve correctness, security, documentation,
compatibility, or maintainability without expanding the frozen platform scope.

## Development setup

```bash
python -m pip install -e ".[dev]"
```

## Contribution workflow

1. Search existing issues and read [SUPPORT.md](SUPPORT.md) for the appropriate
   community channel.
2. Propose broad API, SDK, Extension, Marketplace, or lifecycle changes through
   [RFC_PROCESS.md](RFC_PROCESS.md) before implementation.
3. Keep a pull request focused and describe motivation, compatibility impact,
   validation, documentation changes, and any operator action.
4. Update tests and public documentation whenever behavior or a public contract
   changes.

## Quality checks

Run the relevant checks before opening a pull request:

```bash
ruff check src tests benchmarks
mypy src/manga_director
pytest
```

## Contribution requirements

- Keep workflow rules in `StateMachine` and `WorkflowEngine`, never in CLI,
  API, MCP, agents, or adapters.
- Preserve exactly one Page per workflow execution, storyboard persistence
  before image generation, completed quality review before approval, and
  explicit approval.
- Preserve public Python API, CLI, FastAPI/REST, MCP, Web UI, Repository, SDK,
  Plugin, and Extension compatibility.
- Use typed Pydantic models at public boundaries and avoid provider-specific
  branches in core services.
- Treat Plugin and Marketplace proposals as descriptor and compatibility work;
  do not add remote installation or publication behavior to v6.x LTS.

## Pull-request review

Maintainers review security, workflow invariants, public surfaces, package
metadata, and release documentation. See [GOVERNANCE.md](GOVERNANCE.md),
[DEPRECATION_POLICY.md](DEPRECATION_POLICY.md), and [ROADMAP.md](ROADMAP.md).
