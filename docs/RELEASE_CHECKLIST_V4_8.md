# v4.8.0 Release Checklist

| Check | Status |
| --- | --- |
| RC1 feedback triaged; no scope-expanding change applied | Complete |
| Version synchronized to `4.8.0` | Complete |
| Changelog, release notes, migration guide, SBOM, and license report updated | Complete |
| v4.7 compatibility and protected workflow regression checks | Complete locally |
| v4.8 integration, static analysis, web checks, package, benchmark, and security audit | Complete locally |
| Final documentation links checked | Complete locally |
| Tag, signed GitHub Release, PyPI upload, and protected CI | Maintainer action required |

## Required publication order

1. Review the final artifacts and protected CI results.
2. Create and sign tag `v4.8.0`.
3. Publish the GitHub Release using `GITHUB_RELEASE_V4_8.md`.
4. Upload the verified wheel and source distribution to PyPI.
5. Monitor the post-release dependency and security channels.

