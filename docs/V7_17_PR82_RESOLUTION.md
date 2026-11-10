# V7-17 PR 82 corrective work record

Date: 2026-11-10 JST.
Historical corrective-work baseline: `00c79f6a786d3c37794e06835034e737512c3c49` on
`feat/v7-17-explicit-storyboard-input`.
Current evidence status: HOLD / final RFC-V7-015 acceptance remains open.
Model routing: GPT-6 Luna High was requested for normal work; actual primary
runtime model/reasoning setting is UNVERIFIED. GPT-6.1 Sol High was requested
for the independent review; its actual runtime model/reasoning setting is also
UNVERIFIED.

## Historical PR and CI evidence (2026-11-10)

The local branch is `feat/v7-17-explicit-storyboard-input` at
`b65a5fa6023e96bac53e9701fa8fe3cf3a551442`; it matches the latest GitHub PR
#82 head. PR #82 is open, draft, and targets `v7-dev` at base
`e1863ed436e381c4f055d7169ff4c90441826a93`. GitHub reports 10 commits and 32
changed files. The live PR description records these current counts.

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

The original seven-path list is recorded in the PR audit
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
historical approval or rejection for the three then-deferred files. The current
remaining adoption hold is safe missing-project handling; the Linux fence-test
shape and fingerprint-exclusion retention approvals are described below.

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

Safe missing-project handling remains deferred. The accepted Linux test shape
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
