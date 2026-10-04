# v2.7.0 RC1 Package Audit

The package remains a typed Python distribution with a Hatch dynamic version
read solely from `src/manga_director/_version.py`. Wheel and source distribution
contents include the package, `py.typed`, prompts, README, license, changelog,
docs, and examples. Runtime dependencies remain Pydantic, PyYAML, Typer, and
SQLAlchemy; PostgreSQL, migrations, and FastAPI stay opt-in extras.

The SBOM and dependency license report are aligned with `2.7.0rc1`. The web
package uses the npm-equivalent `2.7.0-rc.1`. Package metadata and artifacts
must be rebuilt and checked for the exact RC tag before publication.
