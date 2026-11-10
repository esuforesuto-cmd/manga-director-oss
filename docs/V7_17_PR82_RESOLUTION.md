# V7-17 PR 82 corrective work record

Date: 2026-11-10 JST.
Baseline: `00c79f6a786d3c37794e06835034e737512c3c49` on
`feat/v7-17-explicit-storyboard-input`.
Status: HOLD pending the user's disposition of three inherited changes.

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
| tests/test_local_file_project_fence_linux.py | Historical exact-path approval not recovered | User explicitly deferred current adoption in this chat |
| .gitleaksignore | Historical exact-path approval not recovered | User explicitly deferred current adoption in this chat |

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
The path entered the PR in commit `2d5233a`. The two remaining
historical evidence gaps concern the Linux fence test in `69b4417`
and `.gitleaksignore` in `e5298a0`.

The current deferral does not establish historical approval or rejection.
The three deferred files were not edited by this corrective work.

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

## Remaining boundary

The independent reviewer recommends retaining the three deferred inherited
changes for safe missing-project handling, lock timing measurement, and the
single historical synthetic-secret exception. The user chose to defer their
adoption after this recommendation. Approval-record closure and PR completion
therefore remain HOLD.

The final browser test is a mocked-API UI test. It does not establish the
complete browser-to-LocalFile production flow or Linux execution. Current-source
GitHub CI and publication remain separate from these local verification results.
The corrective changes remain local pending the deferred-scope decision and
explicit commit/push/PR-update authorization.
