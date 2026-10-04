# v4.5 RC1 Package Audit

The release-candidate package audit verifies:

- canonical dynamic Python version `4.5.0rc1`;
- frontend prerelease metadata `4.5.0-rc.1`;
- wheel and source distribution creation;
- Twine metadata validation;
- `py.typed` inclusion;
- MIT license inclusion;
- optional extras and public package exports; and
- isolated wheel installation/import smoke verification.

The artifact audit does not publish any package. Tagging, signing, GitHub
release creation, and PyPI upload remain maintainer-controlled release steps.

See [the release checklist](RELEASE_CHECKLIST_V4_5_RC1.md).
