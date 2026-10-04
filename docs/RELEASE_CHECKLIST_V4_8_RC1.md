# v4.8.0 RC1 Release Checklist

## Candidate contents

- [x] Version synchronized to `4.8.0rc1` (`4.8.0-rc.1` for the frontend).
- [x] No functionality beyond the reviewed v4.8 Creative Operating System iterations is added.
- [x] Release notes, architecture, compatibility, workflow, benchmark, security, package, and readiness records are present.
- [x] Changelog and README identify the RC and v4.7 compatibility baseline.

## Local release validation

- [x] Regression, compatibility, architecture, integration, and end-to-end tests pass.
- [x] Formatting/lint and type validation pass.
- [x] Creative Operating System benchmark completes with bounded provider-free DTO composition.
- [x] Local dependency security audit reports no known vulnerable auditable installed dependency.
- [x] Wheel and sdist build, metadata validation, and installed-wheel smoke pass.
- [x] Documentation links and RC quality gates validate.

## Maintainer-controlled publication

- [ ] Confirm protected CI results for the candidate commit.
- [ ] Create and sign the `v4.8.0rc1` tag.
- [ ] Create the GitHub pre-release from [RC release notes](../RELEASE_V4_8_RC1.md).
- [ ] Upload signed artifacts to PyPI when approved.

The unchecked items require repository credentials and release authority not
available to local RC verification.
