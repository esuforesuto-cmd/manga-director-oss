# v5.0.0 RC1 Release Checklist

| Check | Status |
| --- | --- |
| Version synchronized to `5.0.0rc1` / `5.0.0-rc.1` | Complete |
| Architecture, compatibility, workflow, security, package, benchmark, and readiness records created | Complete |
| Regression, compatibility, integration, static analysis, and documentation checks | Complete locally after RC validation |
| Package build, Twine metadata, isolated-wheel smoke, and benchmark | Complete locally after RC validation |
| Static security boundary checks | Complete locally after RC validation |
| External dependency vulnerability lookup | Explicit maintainer approval required |
| Protected CI, signing, RC tag, GitHub pre-release, and PyPI publication | Maintainer action required |

## Publication order

1. Review protected CI and the RC readiness report.
2. Create and sign tag `v5.0.0rc1`.
3. Publish the GitHub pre-release using the release notes.
4. Upload verified artifacts to PyPI only after maintainer approval.
