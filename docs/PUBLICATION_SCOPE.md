# Public Release Publication Scope

## Authority

This tracked policy classifies material before any public GitHub or package
publication. It does not authorize a remote, push, tag, release, or upload.
The stable release authority is `6.0.0`; the active maintenance baseline is
`6.0.x` LTS.

## Classification

| Category | Included material | Publication treatment |
| --- | --- | --- |
| `PUBLIC_RELEASE_CONTENT` | `src/manga_director/`, package metadata, supported examples, stable v6.0 documentation, license, contribution, security, and release-policy material | Included in a reviewed release artifact when otherwise applicable. |
| `PUBLIC_HISTORICAL_REFERENCE` | Versioned release notes, changelog history, v6.0 baseline manifest and historical v6.0 artifacts | Retained as immutable historical evidence; never presented as the current release procedure or selected for publication. |
| `EXPERIMENTAL_PUBLIC_REFERENCE` | `docs/roadmap/POST_V6_1_ROADMAP_PROPOSAL.md` and POST-v6.1 I01–I06 readiness descriptions | May be visible as a clearly labelled pre-release reference. It is not stable, released, or execution authority. |
| `INTERNAL_NOT_FOR_PUBLIC_RELEASE` | CEOS I02 authorization/design records, `MD_FUTURE_*` design records, `source-repository-unchanged.md`, private CEOS source/tests, and the two `MD_POST_LTS_RFC_01_*` internal roadmap records | Must not be included in a public package artifact. They must be separated from a public repository before a public remote is configured. |

`CEOS I02` historical records do not authorize a new public I02 scope.
`I02_AUTHORITY` for this release is **ABSENT**.

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
boundary for the internal roadmap records. Current-candidate verification checks
the source version, wheel and sdist metadata, all declared extras (including
`openai==3.0.0`), SHA-256 values, excluded internal records, and Twine metadata.

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

Before the separately authorized public GitHub phase, maintainers must review
this classification, ensure every `INTERNAL_NOT_FOR_PUBLIC_RELEASE` item is
absent from the intended public repository, run the package verifier, obtain a
current advisory audit, and pass hosted CI. This repository intentionally has
no remote or upstream now: no push or tag/release creation has occurred.

Hosted runner images and dependency resolution within the declared bounded
Python ranges remain mutable external inputs. Immutable action commits, exact
artifact digests, and the recorded clean-environment dependency report make
those surfaces explicit rather than claiming they are fully locked.

## Dependency and advisory evidence

Python dependency provenance is **PARTIAL**: `pyproject.toml` is the tracked
declaration source, while no Python lockfile currently records one resolved
environment. The committed Web lockfile is a separate Web-only boundary and
does not establish Python resolution. The current vulnerability status is
**UNVERIFIED** until a maintainer runs the approved live advisory review against
the clean, recorded dependency environment. This policy makes no unsupported
CVE-free claim.
