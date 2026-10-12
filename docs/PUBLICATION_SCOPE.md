# Public Release Publication Scope

## Authority

This tracked policy classifies repository and package material for public
maintenance and any separately authorized package publication. It does not
authorize a push, tag, release, or upload.
The stable release authority is `6.0.0`; the active maintenance baseline is
`6.0.x` LTS.

## Classification

| Category | Included material | Publication treatment |
| --- | --- | --- |
| Current release content | `src/manga_director/`, package metadata, supported examples, stable v6.0 documentation, license, contribution, security, and release-policy material | Included in a reviewed release artifact when otherwise applicable. |
| Historical reference | Versioned release notes, changelog history, v6.0 baseline manifest and historical v6.0 artifacts | Retained as immutable historical evidence; never presented as the current release procedure or selected for publication. |
| Experimental roadmap reference | `docs/roadmap/POST_V6_1_ROADMAP_PROPOSAL.md` and POST-v6.1 I01–I06 readiness descriptions | May be visible as a clearly labelled pre-release reference. It is not stable, released, or execution authority. |
| Excluded private material | Private authorization, design, source, test, and roadmap records | Excluded from the public repository and public package artifacts; their absence does not grant implementation authority. |

Pre-release roadmap records do not authorize implementation. I02 remains not
started and not authorized.

## Enforced package boundary

The tracked `dist/manga_director-6.0.0.tar.gz` and
`dist/manga_director-6.0.0-py3-none-any.whl` files are
`CANONICAL_HISTORICAL_RELEASE_EVIDENCE` as recorded in the IMP-08 snapshot
freeze. They are immutable, hash-preserved compatibility/reference evidence.
They must never be overwritten, replaced, or selected automatically for a new
publication.

The only current-publication candidate location is the ignored,
repository-relative `build/publication-candidate/` directory. A candidate is a
fresh wheel/sdist build from the current source state, not historical evidence.
`scripts/build_publication_candidate.py` refuses a non-empty candidate directory
and writes a provenance manifest with the source HEAD, working-tree fingerprint,
version, and artifact hashes. `scripts/verify_release_artifacts.py` has two
explicit modes: `historical-baseline` verifies the frozen hashes, while
`current-candidate` accepts only that fixed candidate directory. It fails if the
candidate is absent, stale, ambiguous, or metadata-inconsistent; it never falls
back to `dist/`.

The source-distribution exclusion list in `pyproject.toml` is the package
boundary for excluded private roadmap records. Current-candidate verification
checks the source version, wheel and sdist metadata, all declared extras
(including `openai==3.0.0`), SHA-256 values, excluded private records, and Twine
metadata.

Run, from a clean checkout:

```text
python scripts/verify_release_artifacts.py historical-baseline
python scripts/build_publication_candidate.py
python scripts/verify_release_artifacts.py current-candidate
```

This verifies explicitly selected candidate artifacts and therefore does not use
a possibly stale editable, globally installed, or historical
`manga-director` package. The release record must retain the command output,
artifact digests, interpreter version, and resolved dependency report from the
clean verification environment.

## Publication gate

Before any separately authorized tag, GitHub Release, or package publication,
maintainers must review this scope, confirm excluded private material remains
absent, run the package verifier, obtain a current advisory audit, and pass
hosted CI. This public repository is the source location; push, tag, release,
and package publication remain separate maintainer-controlled actions.

Hosted runner images and dependency resolution within the declared bounded
Python ranges remain mutable external inputs. Immutable action commits, exact
artifact digests, and the recorded clean-environment dependency report make
those surfaces explicit rather than claiming they are fully locked.

## Dependency and advisory evidence

Python dependency provenance is **PARTIAL**: `pyproject.toml` is the tracked
declaration source, while no Python lockfile currently records one resolved
environment. The committed Web lockfile is a separate Web-only boundary and
does not establish Python resolution. Any separately authorized package
publication must record a fresh advisory review against the clean dependency
environment. This policy makes no standing CVE-free claim.
