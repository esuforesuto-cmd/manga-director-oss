# v4.8 RC1 Package Audit

The release-candidate package audit verified:

- canonical dynamic Python version `4.8.0rc1`;
- frontend prerelease metadata `4.8.0-rc.1`;
- SBOM package metadata `4.8.0rc1`;
- non-isolated local wheel and source distribution creation;
- Twine metadata validation for both artifacts;
- inspected `py.typed` and MIT license inclusion in both artifacts;
- optional extras and public package exports; and
- local installed-wheel import smoke verification of the v4.8 Creative
  Operating System governance export.

Generated artifacts are retained under `outputs/v4_8_rc1/dist/`:
`manga_director-4.8.0rc1-py3-none-any.whl` and
`manga_director-4.8.0rc1.tar.gz`.

The audit does not publish any package. Tagging, signing, GitHub release
creation, and PyPI upload remain maintainer-controlled release steps.

See [the release checklist](RELEASE_CHECKLIST_V4_8_RC1.md).
