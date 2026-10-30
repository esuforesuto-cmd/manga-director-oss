# RFC-V7-014: Panel-Aware Page Output Proof Bridge

- Status: Implemented; PR #71 merged into `v7-dev` at `8ca2a8098b41f3acc5c403c0aae7c3dd35b2f791` on 2026-10-29 17:04:54 UTC (2026-10-30 02:04:54 JST)
- Related roadmap item: V7-16
- Prerequisites: completed V7-07 through V7-15 and RFC-V7-005 through RFC-V7-013
- Scope: private LocalFile quality and approved-download proof composition

## Problem

Panel-aware activation can persist a deterministic composite as a Page's
logical output asset. Existing quality and approved-download composition use
the legacy Provider-generation proof chain, so they cannot independently
prove that the selected output is the exact applied composite. This bridge
connects those consumers to the existing `LocalPageOutputProofResolver`.

## Frozen authorities

The bridge introduces no new authority. It reuses the closed resolver's
exactly-one selection across the legacy Provider proof and deterministic
composition proof. A successful result contains the exact already-verified
PNG bytes and their release capability. Invalid, prepared, ambiguous, stale,
or mismatched state fails closed. A found legacy proof and a found composition
proof together are invalid; two missing proofs are unavailable.

Composition authorities are read through their existing `observe_page_at`
read-only inventory APIs. The composite asset is read through a private
read-only adapter: SQLite opens with `mode=ro`, `query_only=ON`, exact schema
and rollback-journal checks; WAL, SHM, or journal sidecars are rejected. The
registered asset row, storage name, byte limit, digest, dimensions, and PNG
structure remain validated. The ordinary owner constructor and writable
`read_verified` path are not used by quality or download reads.

The resolver is constructed per request with an immutable Project/Page scope.
No shared mutable current-Page state is used. Existing whole-page integrity
observations remain authoritative; every matching inventory must identify the
same single composition attempt and exact requested composite asset. Partial,
orphaned, cross-Page, duplicate, prepared, or inconsistent inventory is
rejected.

## Application behavior

- LocalFile API composition supplies one shared proof resolver to the existing
  logical-output quality gate and approved-asset download service.
- Quality requires the existing exact `Generated` state and closed logical
  image descriptor. It resolves and releases one output proof before allowing
  the existing quality workflow to continue.
- Approved download retains all existing approval artifact, terminal history,
  exact Page, strict PNG, byte, and lease checks. It returns the exact bytes
  supplied by the resolver and releases the capability exactly once.
- Existing legacy Provider proofs continue through the same resolver and
  `SafeLocalGeneratedAssetPresenter`; composite outputs use the deterministic
  composition authorities.
- No HTTP route, DTO, public Python export, StateMachine transition, workflow
  action, persisted field, schema, dependency, retry, fallback, or Provider
  call is added.

## Input limitation

The bridge proves an already-produced output; it does not make an incomplete
Storyboard eligible for panel-aware generation. In particular, absent
explicit `narrative_intent`, stable character identities, continuity
bindings, concrete action/background/composition/constraints, or supported
layout geometry remain upstream conversion failures. It must not infer,
repair, or persist these values.

## Validation

### Earlier verification snapshot (before explicit-close stabilization)

Historical status: **incomplete**. The following results precede the final
stabilization evidence below and are retained as failure evidence.

On 2026-10-29, with Python 3.12.14, SQLite 3.53.1, and the existing cached
dependencies (no dependency install or update):

- The five focused Proof Bridge test files produced **88 passed, 1 skipped,
  1 failed** in one run. The initial two concurrent POSTs in the required
  FastAPI E2E both returned 409 (`generation_blocked` and
  `recovery_required`), so that run did not reach the display/quality/visual
  review/approval/download assertions.
- The same E2E passed alone once (**1 passed in 38.41s**), and the HTTP test
  file passed alone once (**30 passed**). The full suite also passed this E2E,
  but the focused suite failure means the concurrent success condition is not
  reproducibly established.
- The full suite produced **3503 passed, 25 skipped, 1 failed**. Its failure
  was `test_confirmation_tombstones_after_transaction_unavailability` during
  R26 composition initialization, before the test body, with SQLite
  `OperationalError: unable to open database file`. Re-running that test
  alone reproduced the initialization failure. Its cause is unclassified;
  it is not established as either a Proof Bridge regression or an environment
  issue.
- Ruff passed for all five changed Python test files. `git diff --check`
  passed.
- Web checks and the package vulnerability audit were not run because the
  existing Web `node_modules` and audit executables are unavailable; no
  dependencies were installed. The mypy check could not run with the cached
  environment because its import failed on missing `librt.base64`.
- Independent read-only review found P0=0, P1=0, P2=1. The new
  `read_verified_at()` reader uses a SQLite connection context manager, which
  controls transactions but does not explicitly close the handle. This P2
  remains open because this final verification approval permits test and
  document edits only, not Proof Bridge source edits.

The result is **WARN / incomplete**. Preserve the concurrency assertion and
fake Provider submit-count requirement. Do not claim Page E2E completion until
the concurrent path is stable and the full suite is clean or the R26 failure
is otherwise explained. Existing LocalFile Windows security and v6 tests ran
as part of the full suite, which had the single failure above; no separate
clean security or v6-only run is recorded here.

### Historical local stabilization evidence (2026-10-29, before CI fixes)

This snapshot predates the typing/platform correction and hosted verification
below. Its unavailable checks and pre-commit status describe that stage only.

The separately approved source correction wraps the new reader connection in
`contextlib.closing`. It preserves read-only/query-only access and closes the
connection before row and PNG validation. A retained real SQLite connection
subclass verifies exactly one close and an unusable connection after success,
missing rows, an early schema rejection, and an SQL exception.

- Focused five Proof Bridge files plus the complete R26 reconciliation
  finalization module: **127 passed, 1 skipped in 97.91s** with a new short
  basetemp ending in `Manga Director/a1`.
- Full pytest: **3508 passed, 25 skipped in 474.89s** with another new short
  basetemp ending in `Manga Director/a2`. Existing LocalFile Windows security
  and v6 regression tests were included; skipped tests are not PASS claims.
- Both runs preserved the initial two concurrent POST success requirement,
  fake Provider submit-count/at-most-once assertions, approval boundaries,
  read-only checks, and fail-closed conditions.
- The earlier R26 failure is explained by path-length behavior in this
  runtime: its DB path was 253 characters (261 with `-journal`), while the
  successful short-root run used 243 (251 with `-journal`). A separate native
  SQLite probe with no product code reproduced `unable to open database file`
  at `BEGIN IMMEDIATE` for 253/261 and succeeded for 243/251. This is evidence
  about this environment, not a universal Windows/SQLite limit.
- The earlier 273-character staging-file failure is consistent with path
  pressure. The cause of every prior concurrent HTTP failure is not proven;
  the two final short-root test runs passed without weakening their criteria.
- Ruff passed for all nine changed Python files; `git diff --check` passed.
  Mypy was attempted again and could not import `librt.base64`. Web checks
  and external package audits remain unavailable without installing missing
  dependencies/tools, which was not authorized.
- A separate read-only reviewer reported **P0=0 / P1=0 / P2=0** for the
  inspected source and tests; the earlier close P2 is resolved. The main
  runtime identifies as GPT-6.1 Sol. The review was assigned GPT-6.1 Sol High;
  its serving model identity could not be independently attested.

Status at this historical snapshot was **WARN: local stabilization verified, unavailable checks
pending**. No commit, push, PR, merge, CI rerun, dependency update, live
Provider/ComfyUI, I02 activation, or publication was performed. Default
Planning input completeness and live production Page E2E remain outside this
proof bridge's completion claim.

The approved implementation allowlist is exactly the twelve files stated in
the task approval and recorded in the implementation review. Any need to
change another file, persisted schema, public contract, dependency, live
Provider, I02, v6, or `main` requires stopping and a separate approval.

### Current PR verification (checked 2026-10-30 JST)

The verified implementation head is
`3d655888565e86878f6b725299e41d9553a66f13` on
`feature/panel-output-proof-bridge`, with parent
`ef641ba6c00c333da64a210314830c0a13879bb0`. These commits were included in
[PR #71](https://github.com/esuforesuto-cmd/manga-director-oss/pull/71), whose
base was `v7-dev` at `7aec88910f427aaf577567988fc9375d9e5e1cca` (11 changed
files). PR #71 was merged into `v7-dev` at
`8ca2a8098b41f3acc5c403c0aae7c3dd35b2f791` on 2026-10-29 17:04:54 UTC
(2026-10-30 02:04:54 JST).

The first pushed implementation encountered eight mypy errors in two files
and a Linux Quality E2E failure in CI run `40869804420`. The correction keeps
the existing Protocol/None contracts and separates OS-specific test tails;
it does not add Linux Quality support or change its Windows safety fence.

Local evidence for the corrected source/test snapshot is **3509 passed,
26 skipped** for Windows full pytest and **122 passed, 7 skipped** for the
focused regression. Isolated Python 3.12.14 with mypy 1.20.2 and librt 0.16.0
passed Linux-target mypy (320 source files) and Windows-target mypy
(326 source files), both with zero errors. Ruff and `git diff --check`
passed. Source/test SHA-256 checks matched the verified snapshot. These
results supersede the earlier environment-blocked checks; they do not
rewrite those historical failures. Local native Linux execution was
unavailable, and is distinguished from the hosted native Linux results.

[Push CI run 40879933045](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/40879933045)
passed 10/10 jobs at this head. Separately,
[PR CI run 40889434951](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/40889434951)
completed successfully with **10/10 jobs** for the same PR head. PR CI checked
out GitHub's synthetic merge `e20a7c58d09f3026f713b5ba0e6cfad648f487b6`
(head into the base above); GitHub compare reports no file changes between
that merge and the head. CodeQL checked out the head directly. Measured PR
CI results are:

| PR CI validation | Result |
| --- | --- |
| Native Linux Python 3.11 / 3.12 | Each 3211 passed, 324 skipped |
| Native Windows Python 3.11 / 3.12 | Each 3513 passed, 22 skipped |
| static-analysis | Ruff PASS; Linux mypy: 320 source files, zero errors |
| windows-localfile-security | Windows mypy: 326 source files, zero errors; 12 tests passed |
| frontend | lint, typecheck, unit tests and build PASS |
| real-delivery-e2e | Existing browser E2E job PASS |
| security | pip-audit, npm audit and gitleaks PASS |
| package | PASS |

[CodeQL run 40889430435](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/40889430435)
passed **3/3** analyses: Actions, Python, and JavaScript/TypeScript. Skipped
tests are not PASS claims; job success is not proof of live production E2E.

The real FastAPI tests use a fake panel transport. Common generation tests
retain at least one 200 response in the first two concurrent POSTs and one
Provider submission across retries. Windows verifies display, Quality,
Visual QA, explicit human approval, download, and reconstruction. Linux
verifies `PAGE_EXECUTION_FENCE_UNAVAILABLE` at Quality with unchanged state,
files, events and zero Quality-agent calls. This preserves fail-closed
behavior rather than claiming a complete Linux review workflow.

Existing separate read-only implementation/fix reviews reported
**P0/P1/P2 = 0/0/0**. The PR's documentation-freshness P2 is addressed by this
documentation update. Hosted results above apply to the implementation head;
they do not establish validation of a later documentation commit.
[Post-merge CI run 40917858948](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/40917858948)
on the merge commit completed successfully with **10/10 jobs**, and
[post-merge CodeQL run 40917858812](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/40917858812)
completed successfully with **3/3 analyses**. These runs verify the merged
implementation snapshot, not a later documentation-only change.
Default Planning input completeness, live
Provider/ComfyUI, full live production Page E2E and I02 remain outside the
completion claim.

## Authorization

This RFC and the exact approved implementation scope authorize only the
private bridge work and its local validation. They do not authorize commit,
push, pull request, merge, CI rerun, branch deletion, release, publication,
live ComfyUI, I02, schema migration, dependency changes, or changes to `main`
or v6.
