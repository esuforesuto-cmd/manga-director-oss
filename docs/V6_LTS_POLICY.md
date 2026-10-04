# v6.x LTS Policy

## Stability promise

The `6.0.x` line maintains Platform API v1.0, SDK v1.0, Extension API v1.0,
and Marketplace Specification v1.0 as additive, read-only contracts. Security
and correctness fixes must preserve their existing signatures and behavior.

## Maintenance changes

Allowed changes are bug fixes, security fixes, documentation corrections,
compatibility validation, and performance repairs that preserve observable
behavior. New execution, approval, publication, repository mutation,
Extension lifecycle, or Marketplace network behavior is outside v6.x LTS.

## Deprecation and escalation

Any future deprecation requires a documented migration path and a later major
release. POST-v6.1 I01–I06 readiness evidence is additive pre-release work; it
does not by itself amend the stable `6.0.0` LTS contract or authorize I02.
External CVE remediation, signing, hosted CI, and Marketplace publication remain
owner-controlled operational activities.
