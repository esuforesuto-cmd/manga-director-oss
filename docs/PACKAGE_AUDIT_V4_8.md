# v4.8.0 Package Audit

## Validated release artifacts

| Artifact | Expected result |
| --- | --- |
| Wheel | `manga_director-4.8.0-py3-none-any.whl` builds and metadata validates. |
| Source distribution | `manga_director-4.8.0.tar.gz` builds and metadata validates. |
| Typed package marker | `py.typed` is included. |
| License | `LICENSE` is included in release artifacts. |
| Package exports | `manga_director.__version__` and v4.8 additive production exports import after wheel installation. |
| Optional extras | Declared extras remain package metadata only; no new extras are introduced. |

## Publish boundary

Artifacts are ready for maintainer signing and upload. This repository does
not create a tag, GitHub Release, or PyPI upload automatically.

