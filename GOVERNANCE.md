# Governance

`manga-director` uses a maintainer-led, evidence-based governance model.

## Responsibilities

- Maintainers review public APIs, workflow invariants, security, package
  metadata, release assets, and LTS compatibility decisions.
- Contributors propose changes through issues, pull requests, and the
  [RFC process](RFC_PROCESS.md).
- Reviewers verify that StateMachine authority and the one-Page workflow
  invariants remain intact.

## Decisions

Routine fixes are accepted through normal review. Changes to public APIs, SDK,
Extension compatibility, Marketplace certification, deprecation, security
boundaries, or lifecycle policy require an RFC and maintainer decision recorded
in the pull request or issue. Breaking changes require a future major-version
migration plan.

## Safety and conduct

Security reports follow [SECURITY.md](SECURITY.md), not public issue threads.
Community conduct follows [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Maintainers
may pause or reject a change that lacks compatibility, quality, or safety
evidence.
