# IMP-08 canonical snapshot freeze

## Record

- Authorization: `MD_POST_LTS_RFC_01_SNAPSHOT_MANIFEST_AND_HASH_FREEZE_01`
- Previous decision: `MD_POST_LTS_RFC_01_GIT_HISTORY_LOSS_DECISION_REVIEW_01`
- Canonical completed milestone: `MD_POST_LTS_RFC_01_IMP_08_COMPLETE_AND_VERIFIED`
- Mode: baseline manifest and hash freeze only
- Primary manifest: `MD_POST_LTS_RFC_01_IMP08_CANONICAL_SNAPSHOT_MANIFEST.sha256`
- Primary manifest SHA-256: `58ad4cef5c8e0de430a6f3dd128a09b76452dcd7dca7a0280366a428f6a3cf82`
- Canonical file count: 2,682
- Canonical total bytes: 10,124,121

This record freezes the exact authoritative IMP-08 `COMPLETE_AND_VERIFIED`
source snapshot before any replacement Git repository is initialized. Manifest
paths are normalized forward-slash paths relative to the canonical snapshot
root. Absolute paths, timestamps, filesystem object identities, and this
record itself are not canonical identity inputs.

## Inclusion policy

The canonical inventory includes:

- all production files under `src/manga_director/`;
- all tests under `tests/`;
- all authoritative documentation under `docs/`, except the two baseline
  records created by this freeze to avoid a circular hash dependency;
- handwritten project automation and configuration under `.agents/`,
  `.codex/`, `.github/`, `benchmarks/`, `examples/`, `migrations/`, `scripts/`,
  and the non-generated portions of `web/`;
- canonical root metadata, packaging configuration, release records, policies,
  security material, contribution material, and build orchestration files; and
- the accepted v6.0.0 source distribution and wheel as historical release
  evidence.

Every primary-manifest record has the deterministic form
`<SHA256>  <normalized-relative-path>`. Records are unique and sorted
lexicographically by normalized relative path. The primary manifest does not
hash itself or this freeze record.

## Exclusion policy

Excluded material is non-canonical and is not required to reconstruct the
source state. Nothing was deleted. Counts are informational observations from
the freeze pass and are not canonical identity inputs.

| Pattern or category | Reason | Observed file count | Affects source reconstruction |
| --- | --- | ---: | --- |
| `.git/` | Empty/corrupt former Git metadata | 0 | NO |
| Primary manifest and freeze record | Circular self-hash prevention | 2 | NO |
| `__pycache__/`, `*.pyc`, `*.pyo`, pytest/mypy/Ruff caches | Generated interpreter and tool caches | 26,178 | NO |
| Coverage, profile, OS-generated files | Generated verification or machine state | 3 | NO |
| Virtual and verification environments | Machine-specific dependency/runtime state | 23,381 | NO |
| Build and package-verification scratch | Re-creatable build intermediates | 366 | NO |
| `outputs/`, `t/`, and test temporary roots | Temporary verification/output state | 35,810 | NO |
| Temporary logs, SQLite databases, journals, WAL/SHM files | Runtime and test state | 9,951 | NO |
| `web/node_modules/`, `.next/`, `.npm-cache/`, test results | Generated web dependencies, cache, and output | 224,072 | NO |
| Ignored local `plugins/` material | Local non-canonical plugin state | 5 | NO |
| Other environment/generated directories | Non-canonical local verification state | 15,953 | NO |
| Other files under `dist/` | Generated duplicates not selected as baseline lineage evidence | 44 | NO |
| Editor/IDE metadata, environment secrets, and OS metadata | Machine-specific state; absent or excluded when present | 0 | NO |

The build, distribution, and output areas were classified individually:

- `dist/manga_director-6.0.0.tar.gz` and
  `dist/manga_director-6.0.0-py3-none-any.whl` are
  `CANONICAL_HISTORICAL_RELEASE_EVIDENCE`;
- the other 44 distribution files are
  `NONCANONICAL_GENERATED_DUPLICATE`;
- build and package-verification directories are generated scratch; and
- `outputs/` and test roots are temporary output.

## Historical v6.0.0 release evidence

- Package/version: `manga-director 6.0.0`
- Source distribution: `dist/manga_director-6.0.0.tar.gz`
- Source distribution SHA-256:
  `e34077a6d894fd803f3565a2d45f028879e88759d7861dca4d4a37d751300bd9`
- Wheel: `dist/manga_director-6.0.0-py3-none-any.whl`
- Wheel SHA-256:
  `b1ff393f8102982b654b5d5c876a1a398e3781e43a57b6a858f76b77fec8778e`
- Relationship: `SAME_LINEAGE_PRIOR_RELEASE_EVIDENCE`

The accepted bounded comparison found 1,898 files in the v6.0.0 source
archive, 1,897 corresponding files in the current snapshot, 1,871
byte-identical files, and 26 evolved files. The sole archive entry absent from
the working snapshot is generated `PKG-INFO`. These release archives establish
source lineage; they do not contain or reconstruct Git history.

## History-loss provenance

The original canonical Git metadata and history for the Python Manga Director
repository are unavailable and were determined effectively unrecoverable by
`MD_POST_LTS_RFC_01_GIT_HISTORY_LOSS_DECISION_REVIEW_01`.

A later new baseline may preserve the current source, tests, documentation,
release-lineage evidence, IMP-08 `COMPLETE_AND_VERIFIED` state, and all future
Git history. It will not preserve or reconstruct original commit ancestry,
authorship chronology, branch ancestry, tag ancestry, merge history, or the
exact pre-baseline commit graph. No future baseline record may imply that this
history was recovered.

## IMP-08 formal state

- `IMP08_IMPLEMENTATION_STATUS = COMPLETE`
- `IMP08_INDEPENDENT_VERIFICATION_STATUS = PASS`
- `IMP08_FORMAL_STATUS = COMPLETE_AND_VERIFIED`
- Canonical completion identifier:
  `MD_POST_LTS_RFC_01_IMP_08_COMPLETE_AND_VERIFIED`

## Accepted verification evidence

- Full repository: 2,783 collected; 2,781 passed; 0 failed; 2 skipped;
  exit code 0
- IMP-08 focused: 43 passed
- IMP-07A regression: 53 passed
- LocalFile/CAS regression: 73 passed
- IMP-07/R30/R31 regression: 139 passed
- v6/LTS: 32 passed
- Ruff: PASS over full `src` and `tests`
- Strict mypy: PASS over the affected production scope
- Compile: PASS
- Open P0 findings: none
- Open P1 findings: none
- Open P2 findings: none

These are accepted prior verification results. The suite was not rerun during
this documentation-and-manifest-only freeze.

## Manifest integrity and re-verification

An independent second pass verified all 2,682 entries after manifest creation:
every file existed, every byte size was stable, and every SHA-256 matched.
The manifest was valid UTF-8, contained only normalized relative paths, was
strictly lexicographically sorted, contained no duplicate paths, and excluded
both baseline records from its own identity domain. Result: `PASS`.

## Future Git initialization boundary

Any later Git initialization requires separate authorization and must use this
manifest as the source boundary. Before the first commit it must exclude the
invalid old `.git/`, preserve and reverify every canonical manifest entry,
exclude transient artifacts, record this history-loss provenance, and create a
new baseline commit without claiming historical continuity. Git initialization,
commit, tag, branch, push, and transfer are outside this freeze.

## Successor hard stop

- `IMP09_IMPLEMENTATION_STATUS = UNAUTHORIZED_NOT_STARTED`
- `IMP09_IMPLEMENTATION_AUTHORIZED = NO`
- `IMP10_IMPLEMENTATION_STATUS = UNAUTHORIZED_NOT_STARTED`
- `IMP10_IMPLEMENTATION_AUTHORIZED = NO`
- `TECHNOLOGY_UPDATE_AUDIT = NOT_STARTED`

The next required gate is `NEW_CANONICAL_GIT_BASELINE_INITIALIZATION`, under a
separate explicit authorization.
