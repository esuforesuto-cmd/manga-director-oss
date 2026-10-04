# v5.0.0 Release Checklist

| Check | Status |
| --- | --- |
| RC feedback triaged; no scope-expanding change applied | Complete |
| Version synchronized to `5.0.0` | Complete |
| Release notes, migration guide, SBOM, license report, and LTS evidence updated | Complete |
| Regression, compatibility, integration, static analysis, web, benchmark, package, and documentation validation | Complete locally |
| Static security boundary checks | Complete locally |
| External dependency vulnerability lookup | Explicit maintainer approval required |
| Protected CI, signing, GitHub Release, and PyPI upload | Maintainer action required |

## Publication order

1. Approve and run the external dependency vulnerability lookup.
2. Review protected CI and final release assets.
3. Create and sign tag `v5.0.0`.
4. Publish the GitHub Release using `GITHUB_RELEASE_V5.md`.
5. Upload the verified wheel and source distribution to PyPI.

