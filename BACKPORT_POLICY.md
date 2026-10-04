# Backport Policy

## Eligible changes

Backports to `6.0.x` are limited to security fixes, correctness fixes,
regressions, compatibility repairs, reliability improvements, and essential
documentation corrections. Each backport must be small, independently tested,
and safe for existing operators.

## Exclusions

New features, API redesign, automatic workflow execution, automatic approval,
remote Extension lifecycle, Marketplace publication, repository format changes,
and dependency upgrades without a concrete fix are not LTS backports.

## Required evidence

Every backport records its source issue or advisory, affected public surfaces,
compatibility assessment, tests, release-note impact, and rollback action.
Security backports also follow [SECURITY_POLICY.md](SECURITY_POLICY.md).
