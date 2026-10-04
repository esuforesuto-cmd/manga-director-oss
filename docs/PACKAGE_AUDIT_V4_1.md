# v4.1.0 Package Audit

| Item | Result |
| --- | --- |
| Version source | Pass — Hatch derives package version from `src/manga_director/_version.py`. |
| wheel | Pass — built as `manga_director-4.1.0-py3-none-any.whl`. |
| sdist | Pass — built as `manga_director-4.1.0.tar.gz`. |
| Twine metadata | Pass. |
| `py.typed` | Present. |
| README / LICENSE | Present. |
| Optional extras | Declared in package metadata. |
| Package exports | Contract tests pass. |
| SBOM / license report | Updated to 4.1.0. |

The local package-install smoke verifies the built wheel can be installed and
imports the canonical stable version without changing workflow authority.
