# RFC-V7-004: Human Visual QA and Approval Readiness

- Status: Design approved; implementation and execution are not authorized
- Target line: v7.0 Discovery (Post-LTS)
- Roadmap item: V7-06 Human Visual QA and Approval Readiness
- Delivery scope: docs-only design
- Decision owner: an explicit human reviewer

## Decision boundary

This RFC freezes the smallest advisory design that connects validated
generation evidence to human visual QA and then to an approval-readiness
result for exactly one existing Page.

The result is one of `ready`, `needs_review`, or `blocked`. It is evidence for
a human decision, not the decision itself. `ready` must never approve a Page,
populate approval identity, call an approval command, or change workflow
state. The existing `StateMachine` remains the only transition authority:
approval is legal only from persisted `QualityChecked` and only through a
separate explicit human approval action.

This RFC adds no implementation, public DTO, endpoint, command, persistence
format, asset reader, image viewer, or workflow behavior. It performs no live
generation and authorizes none.

## Problem

The verified V7 generation chain can persist a validated PNG, generation
evidence, and a registered asset. Existing internal visual-continuity QA can
compare caller-supplied logical evidence and produce a deterministic checklist,
but deliberately does not inspect image bytes, record a human judgment,
approve or reject a Page, or declare approval readiness.

Consequently, generation success cannot by itself answer whether:

1. the exact generated asset and provenance are the evidence under review;
2. a human has actually inspected the visual result;
3. visual findings are resolved, need another review, or block progression;
4. the Page has reached the existing `QualityChecked` boundary; and
5. the evidence package is complete enough for a human to consider the
   separate explicit approval action.

A frozen design is required so a future implementation cannot mistake
generation success, automated QA, or a readiness label for approval.

## Planning summary

- **Title:** V7-06 Human Visual QA and Approval Readiness
- **Objective:** Define a deterministic, read-only evidence flow from one
  validated generation result through explicit human visual judgment to an
  advisory approval-readiness status.
- **Scope:** One existing Project, one existing Page, one exact generation
  attempt, one registered PNG asset, supplied QA evidence, one explicit human
  judgment, and one derived readiness result.
- **Inputs:** Current Page state, validated generation evidence, registered
  asset identity, existing advisory Visual Continuity QA output, and
  caller-supplied human-review evidence.
- **Outputs:** A closed readiness status, ordered findings, missing
  prerequisites, and trace references for the human approval hand-off.
- **Dependencies:** The existing generation-evidence, asset-registration,
  LocalFile containment, `StateMachine`, `WorkflowEngine`, quality-review, and
  explicit-approval boundaries on `v7-dev`.
- **Estimated complexity:** Medium for a separately approved future
  implementation; Low for this docs-only design.
- **Architecture notes:** Composition and validation only. No transition,
  Provider execution, image mutation, reviewer substitution, or public API
  change.

## Goals

- Bind review to one exact Page, generation attempt, output asset, and
  provenance reference.
- Keep deterministic evidence validation separate from subjective human
  visual judgment.
- Define stable, fail-closed precedence for `ready`, `needs_review`, and
  `blocked`.
- Make missing, conflicting, ambiguous, or incomplete evidence visible
  without inferring a favorable result.
- Preserve `QualityChecked` before explicit approval and keep approval a
  separate human action.
- Reuse existing logical references and advisory reports without making them
  public or authoritative beyond their current boundaries.
- Preserve public API and v5/v6 compatibility with no migration.

## Non-goals

- automatic approval, rejection, override, remediation, regeneration, retry,
  fallback, or Provider switching;
- changing the `StateMachine`, `WorkflowEngine`, Page states, transition
  commands, or approval identity requirements;
- deciding artistic quality without a human reviewer;
- using generation success, a quality score, or an automated finding as a
  human judgment;
- reading arbitrary paths or URLs, bypassing LocalFile containment, or
  trusting Provider-supplied filesystem locations;
- creating a public DTO, Python export, CLI command, HTTP endpoint, MCP tool,
  Web UI contract, SDK surface, or Plugin contract in this design phase;
- authentication, authorization, role assignment, notification, routing,
  escalation execution, or access control;
- live image generation, Project creation, Page mutation, asset mutation, or
  approval execution;
- I02, dependency or lockfile changes, `main`, versioning, release, tag,
  publication, Settings, force push, history rewriting, or branch deletion.

## Source contracts

The design composes existing contracts without replacing them:

- `GenerationEvidenceValidationReport` validates caller-supplied generation
  evidence and reports `ready`, `needs_evidence`, `needs_review`, or
  `blocked`; it does not access assets, execute a Provider, persist data, or
  make a reproducibility claim.
- `VisualContinuityQAReport` compares supplied logical continuity evidence,
  returns `blocked` or `needs_human_review`, always requires human review, and
  deliberately records no human decision.
- the registered LocalFile asset remains governed by existing ownership,
  strict-PNG, byte-limit, and configured-root containment boundaries;
- the existing quality command moves a generated Page to `QualityChecked`;
  it does not approve the Page; and
- the existing approval command requires a persisted `QualityChecked` Page
  and explicit human identity before `StateMachine` can move it to
  `Approved`.

Neither the generation-evidence status nor the Visual Continuity QA status is
renamed or reinterpreted by this RFC. V7-06 derives a separate advisory
approval-readiness result from those inputs plus explicit human-review
evidence.

## Frozen architecture

### Evidence flow

The future bounded flow is:

~~~text
validated generation evidence
        |
        v
exact Page / attempt / asset / provenance correlation
        |
        v
advisory Visual QA checklist and findings
        |
        v
explicit human visual judgment
        |
        v
approval readiness: ready | needs_review | blocked
        |
        v
separate human approve action, legal only from QualityChecked
~~~

Every arrow before the final approval action is read-only assessment. No
readiness stage may call the Provider, regenerate an image, modify evidence,
write an approval identity, or execute a workflow transition.

### One-Page review scope

One readiness assessment addresses exactly one existing Page and one selected
generation output. The review identity must include logical references for:

- Project and Page;
- generation attempt;
- registered output asset; and
- generation provenance.

All four must identify the same evidence chain. Duplicate, ambiguous, or
conflicting bindings are `blocked`. The assessment must not choose among
multiple attempts or assets, infer a "latest" result, or silently replace a
missing reference.

### Generation-evidence admission

Generation evidence is admissible only when:

- the validation report is present;
- exactly one supplied envelope matches the declared attempt;
- the Page, attempt, output-asset, and provenance references agree;
- the generation result is complete rather than ambiguous or recoverable;
- the output is the registered, validated PNG governed by existing LocalFile
  ownership; and
- no blocking validation or persistence finding is present.

A structurally valid envelope proves only the supplied evidence relationship.
It does not prove visual quality or human acceptance. Missing review evidence
therefore cannot become `ready`.

### Visual QA boundary

Visual QA has two deliberately separate parts:

1. **deterministic preparation** — canonicalize the supplied logical
   evidence, surface missing or conflicting facts, and produce an ordered
   checklist; and
2. **human inspection** — a named human inspects the exact registered output
   represented by that evidence and records a judgment with rationale.

Existing Visual Continuity QA remains an advisory input. Its structured
criteria can identify confirmed evidence, missing evidence, conflicts, and
items requiring visual inspection. It cannot itself satisfy the human
inspection requirement because it neither reads the asset nor records a human
decision.

The minimum human checklist covers the exact output and records whether the
reviewer considered:

- character identity, face, costume, and props;
- pose, gaze, emotion, and screen direction;
- location, time, composition, and panel intent;
- visible corruption, truncation, watermark, unsafe content, or unintended
  text; and
- any declared continuity comparison to supplied storyboard or neighboring
  panel evidence.

The design does not prescribe an aesthetic score. A checklist item may be
acceptable, require further review, or block progression, with a concise
human rationale.

### Human judgment record

The future record is a closed, immutable, caller-supplied review artifact. It
must bind the reviewer judgment to the same Page, attempt, output asset, and
provenance references used by the admitted generation evidence. It records:

- non-empty reviewer identity;
- review timestamp supplied by the caller;
- checklist outcomes and human-authored findings;
- an overall judgment of acceptable for approval consideration,
  further review required, or blocked;
- concise rationale; and
- optional logical references to a review policy or prior review.

The record is evidence only. It does not authenticate the reviewer, grant a
role, authorize an override, persist itself automatically, or become the
`approved_by` value for a later approval command.

### Approval-readiness status

The status is derived with strict precedence:

| Status | Meaning | Required action |
| --- | --- | --- |
| `blocked` | Evidence integrity, binding, asset safety, or an explicit human stop prevents approval consideration. | Resolve through a separately authorized workflow; do not approve or regenerate automatically. |
| `needs_review` | No blocker is proven, but required evidence, human inspection, rationale, quality completion, or reviewer resolution is incomplete. | Present the missing or unresolved items to a human. |
| `ready` | The exact evidence chain is valid, human visual review is complete and acceptable, the Page is persisted as `QualityChecked`, and no finding remains. | A human may separately consider the existing explicit approval action. |

`blocked` takes precedence over `needs_review`; `needs_review` takes
precedence over `ready`. Unknown, absent, malformed, stale, mismatched, or
ambiguous inputs never default to `ready`.

Examples of `blocked` include:

- duplicate or conflicting Page, attempt, asset, or provenance bindings;
- invalid, unsafe, unregistered, or ambiguous output evidence;
- a generation validation or Visual QA blocking finding; and
- an explicit human judgment to stop or reject the selected output.

Examples of `needs_review` include:

- the human visual judgment is absent or incomplete;
- a checklist item still requires inspection or a second reviewer;
- non-blocking evidence is missing or the reviewer requests revision; and
- the evidence package is otherwise valid but the Page has not yet reached
  persisted `QualityChecked`.

`ready` requires all of the following:

1. exactly one Page and exact generation binding;
2. admitted generation evidence and registered validated asset;
3. complete advisory QA findings and checklist;
4. explicit human visual judgment that the selected output is acceptable for
   approval consideration;
5. persisted Page state exactly `QualityChecked`; and
6. no blocking, missing, conflicting, or unresolved finding.

### Quality and approval separation

Visual QA and approval readiness do not add a state between `QualityChecked`
and `Approved`.

- At `Generated`, evidence and the visual checklist may be assembled, but
  readiness cannot be higher than `needs_review`.
- At `QualityChecked`, a complete evidence package and acceptable human visual
  judgment may produce `ready`.
- `ready` leaves the Page at `QualityChecked`.
- Only a separate explicit `approve` action with non-empty human identity may
  request the legal transition to `Approved`.
- An already `Approved` Page uses its historical evidence; V7-06 does not
  reopen, revoke, or repeat approval.

No report may translate `ready` into an approval command, infer
`approved_by`, or treat a reviewer judgment as transition authority.

## Determinism and traceability

For the same canonical inputs, readiness ordering, findings, missing
prerequisites, and status must be identical. A future implementation must:

- use closed status and finding vocabularies;
- sort findings and checklist items by stable logical keys;
- preserve caller-supplied timestamps rather than generate new ones;
- avoid current-time, filesystem-order, environment, or network dependence;
- avoid selecting an identity, attempt, asset, policy, or evidence version;
- expose exact logical references used for the result; and
- keep human-authored judgment distinct from machine-derived findings.

Trace output must not contain secrets, credentials, raw image bytes, arbitrary
filesystem paths, Provider response bodies, or unbounded metadata.

## Security and privacy

- Logical asset references never become filesystem authority.
- Existing LocalFile configured-root containment remains authoritative for
  any separately approved asset presentation.
- The readiness report contains references and review evidence, not image
  bytes.
- Provider metadata, optional descriptor fields, URLs, and output paths are
  not trusted as review identity.
- A report cannot grant access, authenticate a reviewer, assign permissions,
  or bypass approval policy.
- Sensitive reviewer notes or asset presentation require a separately
  designed redaction and access boundary; this RFC does not add one.
- No network, Provider, model, checkpoint, custom node, download, upload, or
  external service is required or authorized.

## Failure and recovery semantics

Assessment failure is read-only and fail-closed.

- Invalid or ambiguous evidence produces `blocked`.
- Incomplete but non-conflicting review evidence produces `needs_review`.
- No failure path triggers generation, retry, replacement, fallback, asset
  mutation, workflow execution, approval, or notification.
- Recovery consists only of supplying corrected evidence or a new explicit
  human judgment through a separately authorized process.
- A previous `blocked` or `needs_review` report remains historical evidence;
  it is not overwritten or treated as an approval denial.

## Public contract compatibility

This design preserves:

- all current Python imports and public exports;
- CLI, HTTP, Web UI, MCP, SDK, Plugin, Repository, and delivery contracts;
- `StateMachine`, `WorkflowEngine`, Page states, commands, and event meaning;
- one-Page execution and storyboard-before-generation;
- generation-evidence, asset-registration, LocalFile schema, and containment
  behavior;
- mock defaults, OpenAI V7-03, ComfyUI V7-04/V7-05 behavior, and Provider
  neutrality;
- `QualityChecked` before explicit human approval; and
- v5/v6 behavior and project readability.

No migration or rollback action is required because this change is
documentation only. A future implementation that requires any public
contract, persistence, StateMachine, dependency, or I02 change is a scope
expansion and must stop for separate authorization.

## Validation plan

This docs-only change requires:

- exact two-file allowlist review;
- local Markdown-link resolution;
- `git diff --check`;
- confirmation that source, tests, dependencies, lockfiles, workflows,
  package metadata, versions, and settings are unchanged;
- architecture and compatibility review of the described boundaries;
- independent review with P0 = 0 and P1 = 0 before merge; and
- required hosted CI and CodeQL checks for the final commit.

A separately approved future implementation would additionally require
focused deterministic fixtures for every status and precedence rule,
generation/asset binding regressions, StateMachine and explicit-approval
regressions, LocalFile path-safety checks, public-contract tests, full
applicable regression, lint, type-check, security/audit, and package gates.
Those implementation checks are planning only and are not executed by this
RFC.

## Acceptance criteria

The design is accepted when:

1. the evidence flow is explicitly generation evidence → Visual QA → human
   judgment → approval readiness;
2. `ready`, `needs_review`, and `blocked` have deterministic, fail-closed
   meanings and precedence;
3. `ready` is explicitly advisory and cannot approve or transition a Page;
4. persisted `QualityChecked` and a separate explicit human approval remain
   mandatory before `Approved`;
5. one Page and one exact attempt/asset/provenance chain are enforced;
6. existing Visual Continuity QA remains advisory and cannot substitute for
   human image inspection;
7. I02 remains independent and no public API, persistence, dependency,
   Provider, or compatibility change is authorized;
8. the docs-only diff stays within the exact two-file allowlist; and
9. independent review, required CI, CodeQL, and post-merge checks report no
   blocking issue.

## Authorization gate

Approval of RFC-V7-004 authorizes only this docs-only design record and the
matching V7-06 roadmap update. It does not authorize implementation, image or
asset access, live generation, Project or Page mutation, approval execution,
I02, dependencies, `main`, versioning, release, tag, publication, Settings,
branch deletion, force push, or history rewriting.

Any future implementation requires a new exact allowlist, explicit
implementation authorization, applicable security and compatibility review,
and executed quality gates. If implementation requires a new public API,
StateMachine state or command, persistence field, dependency, live operation,
or I02 authority, it is outside this RFC and must stop.
