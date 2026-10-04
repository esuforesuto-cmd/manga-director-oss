# v3.0.0 RC1 Package Audit

The package remains a typed Python distribution with a Hatch dynamic version
read solely from `src/manga_director/_version.py`. Wheel and source distribution
contents include the package, `py.typed`, prompts, README, license, changelog,
docs, and examples. Runtime dependencies remain Pydantic, PyYAML, Typer, and
SQLAlchemy; PostgreSQL, migrations, and FastAPI remain opt-in extras.

The SBOM and dependency-license report are aligned with `3.0.0rc1`. The web
package uses the npm-equivalent `3.0.0-rc.1`. Package artifacts must be rebuilt,
checked, and clean-installed for the exact RC tag before publication.
