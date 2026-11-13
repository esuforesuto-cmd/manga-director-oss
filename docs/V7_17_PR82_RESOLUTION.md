# V7-17 PR 82 corrective work record

Date: 2026-11-10 JST.
Historical corrective-work baseline: `00c79f6a786d3c37794e06835034e737512c3c49` on
`feat/v7-17-explicit-storyboard-input`.
Current evidence status (2026-11-13): HOLD / final RFC-V7-015 acceptance remains open. The historical snapshots below are dated evidence; the latest local candidate and live PR state are recorded at the end of this document.
Model routing: GPT-6 Luna High was requested for normal work; actual primary
runtime model/reasoning setting is UNVERIFIED. GPT-6.1 Sol High was requested
for the independent review; its actual runtime model/reasoning setting is also
UNVERIFIED.

## Historical PR and CI evidence (2026-11-10)

At this historical 2026-11-10 snapshot, the local branch was
`feat/v7-17-explicit-storyboard-input` at
`b65a5fa6023e96bac53e9701fa8fe3cf3a551442`; it matched the GitHub PR #82 head
at that time. PR #82 was open and draft, and targeted `v7-dev` at base
`e1863ed436e381c4f055d7169ff4c90441826a93`. GitHub reported 10 commits and 32
changed files at that time.

CI run [#290](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/42797492065)
was triggered for this PR head and checked out the synthetic merge ref
`6136a7500c36e027f5ae8cd2b77c3e484e1cb5ae` (PR head merged into base). All 10
workflow jobs passed. The separate CodeQL run
[#42797484040](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/42797484040)
passed all 3 jobs with no new alerts in PR code.

| Gate | GitHub result |
| --- | --- |
| Linux Python 3.11 full pytest | 3,244 passed, 334 skipped |
| Linux Python 3.12 full pytest | 3,244 passed, 334 skipped |
| Windows Python 3.11 full pytest | 3,555 passed, 23 skipped |
| Windows Python 3.12 full pytest | 3,555 passed, 23 skipped |
| Windows LocalFile security | Windows path-containment test passed; `mypy --platform win32 src` passed |
| Frontend | lint, typecheck, build passed; Vitest 97/97 passed |
| Playwright on Windows | mock-API E2E 4 passed; real-delivery E2E 5 passed |
| Security | `pip-audit --strict .`, production-only `npm audit`, and Gitleaks passed |
| CodeQL | 3/3 passed; no new alerts in code changed by PR #82 |

At this snapshot, the frontend and Playwright suites ran in separate CI jobs; the mock and
real-delivery suites ran as separate steps in `real-delivery-e2e`. The V7-17
real confirmation success case exercises a browser-to-LocalFile save and reload. Its 409 and 503
cases use browser route mocks; the Python real-Uvicorn test is designed to
exercise loopback HTTP success, conflict, and an injected LocalFile
conditional-commit failure. Event-publication failure has a separate
in-process test. The CI pytest logs are quiet summary output rather than per-test
reports, so the aggregate suite result does not verify that the real-Uvicorn
test executed.

At that snapshot, security evidence was described narrowly. Criteria 7 and 8 remained
unverified in full because the tests do not detect every possible unlabeled
numeric revision representation. The real-Uvicorn disclosure test checks
sensitive values and structured keys across responses, persistence,
observer state, application logs, process stdout/stderr, and actual HTTP access
logs. The then-current textual matcher checks labeled revision/fingerprint
diagnostics. It intentionally does not scan an unlabeled bare integer because
it may equal an allowed Page number or schema version. Thus the RFC's absolute
absence claim for every possible numeric revision representation remains
unproven. The CI snapshot did not establish execution of the real-Uvicorn
numeric-revision disclosure check. Gitleaks passed with the checked-in `.gitleaksignore`; this is a scan
result, not proof that every ignored synthetic-secret exception has a recovered
approval record. The CI npm install displayed 8 moderate findings; the separate
production-only `npm audit --omit=dev --audit-level=high` passed, so no claim is
made that all development dependency advisories are absent.

Linux static-analysis mypy passed with the workflow's configured exclusions:
`_windows_safe_filesystem.py`, `page_execution_fence.py`,
`local_file_durability.py`, `next_generation_local_durable_asset_owner.py`,
`future_real_delivery_i02a_verifier.py`, and
`future_real_delivery_binding_authority.py`. Windows mypy over all `src`
passed. CI did not run mypy over tests, and a full Linux run covering excluded
modules is not established here. The standalone historical test-file mypy
result is not a PR CI result and is not used as acceptance evidence.

GitHub currently has no submitted PR reviews. The earlier local reviewer entry
below applies only to the corrective subset and its actual runtime model and
settings remain unverified; it does not establish a current full-diff
P0/P1/P2 classification. The subsequent independent review of the 2026-11-10
corrective scope is reported separately below. RFC design acceptance, green CI, and full RFC
acceptance are distinct states.

## Authorization

In Codex chat `01a1c2fd-762a-7693-a288-4fd4e44938a3`, the user requested
execution through resolution of the E2E, public API, and approval-record issues.
The user then explicitly selected the current GPT-6 Astra for this work.
The corrective scope is the four Python files listed below, the existing
explicit-storyboard browser spec, and this evidence record.
Existing uncommitted diagnostic changes in that spec were preserved.

The historical approval messages below were recovered from chat
`01a1b6a3-ad95-73a2-b0b5-3c2f0793cdb9`. Their contents, rather than PR
comments or design acceptance alone, establish the listed scopes.

| Inherited path | Evidence | Disposition |
| --- | --- | --- |
| src/manga_director/workflow/engine.py | User message 01a1bf9f-ac4f-7791-a34c-f63cd18af7fb, four-file P2 correction approval | Historical edit approval recovered |
| web/vitest.config.ts | User message 01a1c22d-b6a9-79a1-8ccf-1176e9e356ee, Oxc correction approval | Historical edit approval recovered |
| web/e2e-real/workflow.spec.ts | User message 01a1c232-c6c4-7aa3-83d3-2fa1b408f9a6, three-spec label correction approval | Historical edit approval recovered |
| web/e2e-real/explicit-storyboard-confirmation.spec.ts | Same three-spec approval, plus eight-file commit approval 01a1c240-c375-7b12-99a7-6c2a9005f735 | Historical current-diff inclusion approval recovered |
| web/e2e/explicit-storyboard-input.spec.ts | Same three-spec and eight-file approvals | Historical current-diff inclusion approval recovered |
| tests/test_local_file_project_fence_linux.py | Final test shape and edit removing the whole-test wall-clock assertion while retaining the loser-specific wait bound were approved. The limited `f5dadcd` commit was approved. | Push of `f5dadcd` was separately approved on 2026-11-10 14:04 JST. The original approval associated with `69b4417` remains unrecovered. |
| .gitleaksignore | The two-file limited `e5298a0` commit was approved on 2026-11-09 03:29 JST; its push was separately approved on 2026-11-09 03:39 JST. Retention of the exact existing single-fingerprint exclusion was approved. | Original authorization to create/edit the file remains unrecovered. Later commit, push, and retention approvals do not retroactively establish that initial edit approval. |

The eight-file commit approval explicitly names the five confirmed paths
above, along with the related form and Python/Web regression tests.

At the time of this historical audit, the original seven-path list is recorded in the PR audit
`01a1c2a6-2e59-74d1-8ccc-3586b3d9ff42`. It includes `.gitleaksignore`.
The LocalFile durability file was tracked separately.
The continuation recovered its November 7, 12:08 JST approval for the limited
404/503 correction in chat `01a1b3fa-85a7-7971-9e80-d323d2e80cb1`,
user message `01a1b3fa-8d04-7172-beb3-d39eeb3c8a2f`.
The historical audit `01a1b584-e20c-7c02-9e2f-0425a5532fdf` records
the independent comparison of that approval against the file change.
The path entered the PR in commit `2d5233a`. Remaining historical evidence
gaps concern the original approval associated with the Linux fence test in
`69b4417` and the initial creation/edit authorization for `.gitleaksignore`.

The earlier deferral recorded for the corrective work did not establish
historical approval or rejection for the three then-deferred files. At the
2026-11-10 snapshot, the remaining adoption hold was described as safe
missing-project handling. That claim is superseded: the adopted behavior is
HTTP 404 for a missing Project without creating aggregate or revision sidecars,
and HTTP 503 for damaged durability state; regression coverage is recorded in
`tests/test_localfile_explicit_storyboard_input.py` at lines 956 and 992. The
Linux fence-test shape and fingerprint-exclusion retention approvals are
described below.

## Public API correction

Modified source:

- `src/manga_director/agents/builtin.py`
- `src/manga_director/workflow/durable_execution.py`

The new public `PromptAgent.preflight` was replaced with the internal
`_preflight_explicit_storyboard` hook. Its dedicated caller and test references
were updated. A regression asserts the baseline public members
`execute`, `result`, and `target_state`.

Independent review also found that a replacement Storyboard agent could ignore
the confirmed values. The dedicated gate now rejects unsupported Storyboard
composition and a missing private Prompt hook with bounded HTTP 503 before
dispatch or persistence. Actual invalid prompt input retains HTTP 422.
Ordinary Storyboard replacement dispatch remains covered by regression tests.

Modified tests:

- `tests/unit/test_agents.py`
- `tests/test_localfile_explicit_storyboard_input.py`

## E2E diagnosis and correction

The original working-tree spec reproduced an EPERM failure at its dependency
junction creation in beforeAll, line 138. That JSON result contained an error
location and no server-diagnostics attachment.

The earlier execution command was subsequently recovered from chat
`01a1c2ef-aed9-7d52-8c28-f2286fc34022`. It extracted classification only from
`results[].attachments[].body`, although beforeAll failures can instead carry
diagnostics in `results[].errors[].message`. Reading a test title does not prove
an attachment was generated. JSON reporter inline bodies are base64 encoded
(installed Playwright 1.62.0 runner implementation).

The latest historical raw report remains unavailable. Its precise failure
cannot be retroactively identified from the reproduced failure alone.

The spec now copies installed dependencies to its isolated root instead of
creating a junction. A subsequent restricted run reached readiness probing but
reported HTTP none, request_type_error, and an alive child. With permission,
the same isolated runner passed in normal Windows execution. These results
establish an execution-environment distinction, not a particular firewall cause.

The spec also defaults to Playwright Chromium outside installed Windows Chrome,
recognizes signal exits during teardown, and excludes generated Playwright
artifacts from source copying. Browser assertions and time limits are preserved.

## Executed verification

| Check | Outcome |
| --- | --- |
| Python unit agents, unit prompt pipeline, LocalFile explicit storyboard integration | 44 passed, 2 skipped, exit 0 in normal Windows |
| Ruff on the four changed Python files | PASS, exit 0 |
| Mypy on the two changed Python source files | PASS, exit 0 |
| TypeScript --noEmit --incremental false after final spec edits | PASS, exit 0 |
| Vitest explicit-storyboard-input.test.ts | 4 passed, exit 0 |
| Final isolated explicit-storyboard-input Playwright spec | 1 passed, exit 0 in normal Windows |
| git diff --check | PASS, exit 0 |

The Python skips were the POSIX directory-descriptor case and the real Uvicorn
HTTP-log case because Uvicorn was not installed in the selected environment.
Those reasons belong to this 44-passed/2-skipped run. A separate reported run
of 16 passed and 2 skipped did not preserve the individual skipped test names
or reasons; do not attribute the reasons above to that run. The RFC-V7-015
criteria 7 and 8 impact of those two skips in the 16/2 run is therefore
unverified.
The first unit invocation had a TEMP fixture error; the restricted integration
invocation stopped progressing and was interrupted. The table reports the
subsequent completed normal-Windows verification with a dedicated temp directory.
No dependency installation was performed.

Local diagnostic artifacts are under `.v7-17-resolution-20261110/`.
The final successful browser run is `e2e-hDjhJw`; its summary and raw JSON
report are separate. The runner examines result errors as well as the exact
diagnostic attachment and outputs bounded classification fields.
Raw reports, console logs, caches, and dependency copies are not publication
artifacts and must not be staged.

An independent read-only reviewer was dispatched as GPT-6.1 Sol with high
reasoning. It reported PASS with no outstanding findings in the corrective
scope, including the final portability changes. Actual reviewer runtime
model/settings were not exposed to the reviewer and remain UNVERIFIED.
The main runtime identifies itself as GPT-6 Astra; its reasoning setting is
not independently verified.

## Historical independent review and remaining boundary (2026-11-10)

The independent reviewer assigned as GPT-6.1 Sol High reported no P0 and no
implementation P1 within the reviewed scope. It classified the unresolved
exact-path approval evidence as a P1 approval boundary and the unproven
unlabeled numeric revision case as a P2 verification gap. The requested
reviewer model/reasoning were GPT-6.1 Sol High; actual runtime model/settings
remain UNVERIFIED. Review scope covered the 32-file change list, the three
approval-related diffs, and the authority-to-observer/persistence/CAS/result/
event/API/Web-proxy disclosure paths with their tests. It was a focused review,
not a line-by-line review of every changed file. Do not state a whole-PR
P0/P1/P2 result.

The final Linux fence test shape, its limited `f5dadcd` commit, and the
2026-11-10 14:04 JST push have recovered approvals. The specific original
approval associated with `69b4417` remains unrecovered. The two-file
`.gitleaksignore` commit `e5298a0` and its 2026-11-09 03:39 JST push were
approved, and retaining its exact existing single-fingerprint exclusion was
approved. The initial create/edit authorization for `.gitleaksignore` remains
unrecovered; later approvals do not establish it retroactively. The limited
`src/manga_director/repositories/local_file_durability.py` 404/503 correction
also has a recovered approval record.

At the 2026-11-10 snapshot, safe missing-project handling was recorded as
deferred. That status is superseded by the adopted 404/503 behavior and tests
identified above. The accepted Linux test shape
retains the loser-specific wait bound and removes the whole-test wall-clock
assertion. The existing single-fingerprint exclusion is approved for
retention, while its initial edit authorization remains an evidence gap. CI
success and the historic corrective-subset review do not replace outstanding
approval evidence or a full independent code review.

GitHub CI for the PR head recorded above is complete and green, but the PR
remains open and draft. Full RFC acceptance, complete authorization closure,
and a whole-PR independent implementation review remain outstanding. The
2026-11-10 task made no Python or TypeScript changes and ran no tests. It
updated the two approved documents and PR #82 description. Commit, push,
draft-to-ready, review request, and merge remained outside that authorization.

## Latest local focused verification (2026-11-11)

This section records a subsequent local test-file change and run. The historical
CI and execution records above remain unchanged and refer to their stated
revisions and environments.

Uvicorn 0.54.0 was loaded from a dedicated Windows TEMP installation using the
existing Python 3.12.10 environment. No existing virtual environment or
repository dependency was changed. Four focused tests passed in 8.684 seconds
with exit code 0 and no skips. Two tests ran through in-process HTTP clients.
Two used real Uvicorn over loopback:

- `test_real_uvicorn_storyboard_confirmation_logs_do_not_disclose_internal_values`
  checked HTTP 200 success, HTTP 409 replay conflict, and an injected HTTP 503
  save failure.
- `test_real_uvicorn_cas_and_publication_failure_logs_hide_internal_values`
  checked a true stale-revision CAS failure and an event-publication failure.
  Both returned HTTP 503.

The real-Uvicorn tests inspect response bodies and headers, application logs,
stdout, stderr, and Uvicorn access logs. Their revision sentinels exceed the
uint32 process-ID range, so PID values in Uvicorn startup output cannot
accidentally match the sentinels. Numeric revision checks remain active for
structured values and textual forms. The CAS and event-publication failure
paths read the raw persisted Project payloads and individual Page JSON, inspect
them without relying on model deserialization, and scan both parsed JSON and raw text for
revisions, fingerprints, and existing sensitive markers. Existing Page state,
save state, publication attempt, and event assertions remain in place.

Ruff on the target test file and `git diff --check` passed. An independent
read-only review of these two test fixes reported P0/P1/P2 = 0/0/0 within that
limited scope. GPT-6.1 Sol High was designated for the independent review, but
actual reviewer model and reasoning strength are UNVERIFIED. GPT-6 Luna High
was designated for the implementation, but actual implementation model and
reasoning strength are UNVERIFIED.

The child pytest runs remove coverage-related environment variables and do not
contribute their product-code execution to the parent pytest-cov measurement.
The existing CI coverage threshold is 80%; coverage for the current local
diff was not measured and remains UNVERIFIED. CI #290 ran against the earlier
PR merge ref and did not include the test change, which was uncommitted at
local verification. Its aggregate output does not identify individual
real-Uvicorn test executions. The latest local
result does not establish complete RFC-V7-015 acceptance. Criteria 7 and 8
remain UNVERIFIED pending the full acceptance evidence and remaining review and
authorization boundaries recorded above.

## Historical P1-B approval-history exception (2026-11-11 snapshot)

Two original edit-approval records remain unrecovered:

| Change | Unresolved original approval | Later approvals and treatment |
| --- | --- | --- |
| `tests/test_local_file_project_fence_linux.py` in `69b4417` | The original approval for the operation associated with this commit has not been recovered. | The final test shape, the limited `f5dadcd` commit, and its later push were separately approved. None is treated as retroactive approval for `69b4417`. |
| `.gitleaksignore` in `e5298a0` | The initial authorization to create/edit this file has not been recovered. | The later limited commit, push, and retention of its exact single-fingerprint exclusion were separately approved. None is treated as retroactive initial edit approval. |

Historical disposition: P1-B was recorded as an unresolved approval-history
exception at this snapshot. A later status report cited recovered approval
records, but the current assessment has not revalidated those source messages or
their correspondence to the original edits. This historical section and the
current unresolved disposition are both retained.

## Historical CI evidence preparation and PR state (2026-11-11)

The local CI workflow change adds a named Windows Python 3.12 step for these
exact tests; this workflow change is not yet in the PR head:

- `tests/test_localfile_explicit_storyboard_input.py::test_real_uvicorn_storyboard_confirmation_logs_do_not_disclose_internal_values`
- `tests/test_localfile_explicit_storyboard_input.py::test_real_uvicorn_cas_and_publication_failure_logs_hide_internal_values`

The step disables the repository's quiet default, prints individual test
results, and writes JUnit XML under the runner's temporary directory. The
workflow uploads that XML as `real-uvicorn-test-results`. This change only
configures future CI; no GitHub Actions run has been triggered for it, so its
CI result and artifact are pending. The separate local Windows run recorded
above remains the available execution evidence; the 409 browser E2E result is
also retained and was not repeated for this work.

At this review, local HEAD and PR #82 head are both
`1b6dd1330b975435a49a1713596d86c7f650a6b6`; the PR is open and draft with 11
commits and 32 changed files. Four pre-existing implementation/test files have
local changes that are not included in that head. They contain the P1-A
implementation and focused regression test, plus the 409 conflict reload UI
and its E2E spec. Both real-Uvicorn test bodies and numeric-revision checks are
already in commit `1b6dd13`. This update also changes the workflow and these two
records, so seven tracked paths now differ from the PR head. The earlier
10-commit / `b65a5fa` snapshots above are historical and are not current
metadata. The live PR body has not been updated and retains an earlier claim
that the numeric-revision test change was uncommitted and lacked local
execution evidence. The separate local Windows run is recorded above. The new
individual CI results and JUnit artifact remain pending. No commit, push, PR
update, CI rerun, or merge was performed in that snapshot.

## Latest local candidate and live PR state (2026-11-11)

The local branch `feat/v7-17-explicit-storyboard-input` and live PR #82 head are
at `8973d9fc59c0b9ba2e94a0e183444eb70ffe1f3a`. PR #82 is open and draft,
targets `v7-dev` at base `e1863ed436e381c4f055d7169ff4c90441826a93`, and has 15
commits and 33 changed files. The head is pushed.

CI run
[#294](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/43009302127)
tested the PR merge ref `a923aebf9dc143e4d4c834956a88c2692965b23f` for this
head and base; all 10 jobs passed. CodeQL run
[#43009296264](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/43009296264)
passed all 3 analyses. The Windows Python 3.12 job passed both focused
real-Uvicorn tests in 17.88 seconds. Its [job log](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/43009302127/job/130484567833)
shows the individual results. JUnit artifact
[#13850898729](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/43009302127/artifacts/13850898729)
was published. The XML contents were not independently parsed. No tests were
run for this documentation update.

The historical local candidate snapshot at `5fa6282` had user-reported browser
E2E 2/2 in 28.0 seconds, pytest 15 passed, and Vitest 32 passed. These are
historical local results, not runs on the current head. The previous CI #292
ran against PR head `0b19fdb` with 12 commits and 33 changed files. CI run
[#42950964717](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/42950964717)
passed 10/10 jobs. CodeQL
[#42950960110](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/42950960110)
passed 3/3. The Windows Python 3.12 job in CI #292 passed two real-Uvicorn
tests in 13.23 seconds and
published JUnit artifact
[#13825967183](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/42950964717/artifacts/13825967183).
The earlier real-Uvicorn job log is
[#130294893613](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/42950964717/job/130294893613).
The JUnit XML was not independently parsed. Those hosted results belong to the
previous PR head.

P2-A and P2-B are implemented at this head. The browser measures the exact
serialized confirmation body in UTF-8 bytes and blocks bodies larger than
32,768 bytes before POST. The Python API rejects every nonempty raw query string,
including `?&` and `?&&`, before JSON parsing. ASGI exposes the bytes after the
query delimiter and excludes that delimiter from `raw_path`; therefore the
standard scope alone cannot distinguish a bare trailing `?` from no query.
This does not amend the frozen RFC.

P1-B remains an unresolved approval-history exception. The chat and message
identifiers cited by the prior status report are preserved as claims of
recovered approval. That report identified chat
`01a1b6d6-60fb-7ea2-b28b-941e54e46ed3` (“V7-17 E2E環境を調査”) and user messages
`01a1bbd6-98c1-7f10-8d56-9836632e4910` (2026-11-09 00:46:05 JST) and
`01a1bc5d-03e0-7ea2-a741-70421c087949` (2026-11-09 03:12:54 JST). Their
correspondence to the original edits has not been revalidated for this status.
They do not resolve P1-B here, and later approvals are not applied
retroactively. RFC-V7-015 acceptance criteria 7 and 8 remain on hold. PR #82
remains draft and unmerged.

The earlier statement that safe missing-project handling remained deferred is
superseded. The confirmation route returns HTTP 404 for a missing Project
without creating aggregate or revision sidecars, and HTTP 503 for damaged
durability state. Regression coverage is in
`tests/test_localfile_explicit_storyboard_input.py` around lines 956 and 992.
Historical sections retain their dated evidence and do not describe the current
candidate state.

## Current verification snapshot (2026-11-12)

PR #82 is open, draft, and unmerged. The current PR head is
`faead3947a0b6bd7fd1cad50b843e534ce88ed12`, with 19 commits and 45 changed
files, targeting `v7-dev` at base
`e1863ed436e381c4f055d7169ff4c90441826a93`.

### Approval provenance

The two original user-authored approval messages cited in the previous status
were re-opened and compared with the corresponding edits:

- User message `01a1bbd6-98c1-7f10-8d56-9836632e4910` (2026-11-09 00:46 JST)
  authorizes the Linux fence-test change. Commit `69b4417` contains that test
  change; its roadmap and LocalFile test edits were covered by separate prior
  approved scopes.
- User message `01a1bc5d-03e0-7ea2-a741-70421c087949` (2026-11-09 03:12 JST)
  authorizes the test-file update and a fingerprint-specific `.gitleaksignore`
  entry. Commit `e5298a0` changes those two files and excludes only the recorded
  false-positive fingerprint.

P1-B is resolved for these two approval-history records. This does not complete
the independent review or final acceptance of the entire PR.

### Missing Project and damaged durability

The confirmation route returns HTTP 404 (`not_found`) for a missing Project
without creating Project or revision sidecars. Corrupt or unavailable Durable
state returns HTTP 503 (`activation_unavailable`). The regression test checks
these responses and verifies that diagnostic values are not disclosed.

### CI for the current PR head

[Actions run #43133145305](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/43133145305)
completed with 10 of 10 jobs successful. It tested the synthetic PR merge
commit `07a166c84446ccf1ed4b369e1db80a2cb0d87a58`, which combines head
`faead394` with base `e1863ed`. The earlier check on this head had
7 successful jobs and 3 still running. The Linux Python 3.11 and 3.12 suites
each reported 3,297 passed and 334 skipped. The Windows Python 3.11 and 3.12
full regression suites each reported 3,608 passed and 23 skipped.
[CodeQL run #43133139859](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/43133139859)
passed all 3 analyses.

The [Windows Python 3.12 job log](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/43133145305/job/130901932000)
reports both dedicated real-Uvicorn disclosure tests passed in 17.54 seconds.
GitHub lists the uploaded [JUnit artifact #13907312877](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/43133145305/artifacts/13907312877).
The XML contents were not independently inspected.

### Independent review of the full PR

The independent read-only review covered all 45 changed files from base
`e1863ed` to head `faead394`. It reported zero P0 findings, zero P1 findings,
and six P2 findings:

1. **Access logs on rejection.** The confirmation API rejects nonempty query
   strings, but the stock CLI's Uvicorn access log includes the query. A
   credential carried in a rejected query can therefore appear in the access
   log. The dedicated tests cover canonical URLs and credentials in headers.
   The rejected-query behavior was established by source review
   (`src/manga_director/cli/app.py:1320`, `src/manga_director/api/workflow.py:549`).
2. **Content-Length cardinality.** The API counts headers visible in ASGI.
   h11 can collapse identical duplicate Content-Length fields before ASGI,
   so that check cannot establish the RFC's requirement of exactly one field
   on the wire. The application still bounds the actual request body
   (`src/manga_director/api/workflow.py:526`, `:549`, `:588`, `:1648`).
3. **Execution loading compatibility.** The exported `ProjectLoader` adds
   `load_for_execution()`. The application and recovery paths now use that
   method, which reads from the repository directly and bypasses subclasses'
   existing `load()` overrides. This differs from the RFC's unchanged public
   Python API scope (`src/manga_director/repositories/project_loader.py:87`).
4. **Exact panel input.** The Web form trims continuity and constraint lines
   before sending them, while the RFC requires rejection of untrimmed values
   and the form promises exact preservation. The form counts UTF-16 code
   units, while the Python validator counts Unicode code points
   (`web/components/explicit-storyboard-input-form.tsx:27`, `:44`, `:51`, `:137`).
5. **Web proxy admission.** The proxy forwards some Referer forms that Python
   rejects, including user information or fragments. It can also accept
   coalesced Accept values and forward a single replacement header, so the
   downstream API cannot verify the browser's original header cardinality
   (`web/app/api/projects/[projectId]/pages/[pageNumber]/storyboard/confirm/route.ts:46`, `:61`, `:74`).
6. **Committed evidence references.** The roadmap and the committed resolution
   record identify `8973d9f` as the latest candidate and cite CI #294, which
   belongs to that historical head. Their missing-Project test line references
   have drifted. The no-sidecar assertions for `faead394` start at
   `tests/test_localfile_explicit_storyboard_input.py:976`
   (`docs/ROADMAP_V7.md:2137`, `:2181`, `docs/V7_17_PR82_RESOLUTION.md:349`, `:407`).

### RFC acceptance status

**RFC-V7-015 acceptance criterion 7 remains on hold.** The successful
real-Uvicorn tests support nondisclosure on the exercised paths. The rejected
query can still be logged in the stock server configuration, as recorded in
P2 finding 1.

The reviewed code and tests support criterion 8 for the exercised paths. They
check that the aggregate source revision and fingerprint are absent from the
reloaded Project and confirmation, returned WorkflowResult, canonical event,
and Page detail. The PR remains draft and unmerged, and final acceptance is
on hold.

## Current verification snapshot (2026-11-13)

This section supersedes the 2026-11-12 candidate snapshot above; that earlier
snapshot remains unchanged as historical evidence. PR #82 is open, draft, and
unmerged at head
`b7f47449a80b9b94049eb87cdf1a14c605dc3343`, with 23 commits and 45 changed
files, targeting `v7-dev` at base
`e1863ed436e381c4f055d7169ff4c90441826a93`.

### Changes since the previous independent review

The commits after the review of `faead394` address four reported P2 areas:

- `2e6c0df` disables Uvicorn access logging for the standard CLI API server
  and adds a loopback regression test for a rejected query containing a
  marker value. This covers the standard CLI launch path; a separately
  embedded Uvicorn or ASGI host controls its own logging configuration.
- `2e0f9bf` preserves line input for continuity and constraints, rejects
  surrounding whitespace instead of rewriting the input, and updates the Web
  form to count Unicode code points, matching the existing Python validator.
- `b395d17` tightens proxy checks for Referer and coalesced Accept values.
  This does not establish original wire-level header cardinality after
  server normalization.
- `b7f4744` restores existing `ProjectLoader.load()` override behavior in
  execution loading and validates persisted reserved authority before
  projection. The new `load_for_execution()` method remains an addition to
  the exported class API.

The six P2 findings in the prior independent review are historical findings
against head `faead394`. These four commits address the areas described above;
they do not close every review concern. In particular, the RFC requirement
for exactly one Content-Length field on the wire is not established by the
ASGI-visible header check. The roadmap and PR description also have older
candidate evidence that is outside these two document edits. No new full-PR
independent review has been completed at `b7f4744`.

### CI and CodeQL for the current PR head

[Actions run #43348013493](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/43348013493)
completed with 10 of 10 jobs successful. It tested synthetic merge commit
`0847ab906670aa52e148da3f0a25b53b754ec1c0`, combining head `b7f47449` with
base `e1863ed`. The Linux Python 3.11 and 3.12 suites each reported 3,312
passed and 334 skipped. The Windows Python 3.11 and 3.12 suites each reported
3,623 passed and 23 skipped; Windows Python 3.11 coverage was 88.62%.
[CodeQL run #43348007303](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/43348007303)
passed all 3 analyses.

The [Windows Python 3.12 job](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/43348013493/job/131631955001)
passed both dedicated real-Uvicorn disclosure tests and uploaded
[JUnit artifact #14004265974](https://github.com/esuforesuto-cmd/manga-director-oss/actions/runs/43348013493/artifacts/14004265974).
The XML contents were not independently inspected. The new rejected-query
logging regression is part of the normal test suite; it is separate from the
two-test dedicated Uvicorn step.

### Current acceptance status

The stock CLI API server now disables access logging, and the regression test
checks that the marker in a rejected query is absent from captured logs while
normal response and server error logging behavior remains covered. This
evidence supports the exercised standard CLI path. RFC-V7-015 criterion 7
remains on hold pending the final independent review of the whole PR and
coverage of the stated scope. Criterion 8 is supported for the exercised
paths described in the 2026-11-12 snapshot, subject to that same review.

The CI and CodeQL results are green, but they do not constitute final PR
acceptance. PR #82 remains draft and unmerged. The previously recorded six P2
findings remain part of the review history; no full-PR review at the current
head has yet confirmed the post-fix disposition. Final RFC-V7-015 acceptance
therefore remains **HOLD**.
