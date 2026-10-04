# v4.4 RC1 Release Checklist

## Local RC evidence

- [x] Canonical Python/OpenAPI/MCP version is `4.4.0rc1`; frontend metadata is `4.4.0-rc.1`.
- [x] Architecture, compatibility, Enterprise end-to-end, documentation, and boundary tests are included.
- [x] Regression, integration, lint, type, benchmark, security, and package validations completed locally for RC verification.
- [x] SBOM and dependency-license report identify the candidate version.
- [x] RC release notes and readiness record are linked from the README.

## Maintainer release actions

- [ ] Run protected-branch/tag CI for the exact candidate commit.
- [ ] Perform organization secret scanning, signing, and any required hosted CVE review.
- [ ] Create the GitHub prerelease and upload validated wheel/sdist assets.
- [ ] Publish to the intended package registry only after maintainer approval.

These remaining actions require repository and release credentials and are not
performed by this local review.
