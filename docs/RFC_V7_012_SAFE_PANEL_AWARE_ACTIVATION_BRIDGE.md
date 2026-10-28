# RFC-V7-012: Safe Panel-Aware Activation Bridge

- Status: Complete and verified; private LocalFile-only bridge; public routing disabled
- Related roadmap item: V7-14 Safe Panel-Aware Activation Bridge
- Baseline: `v7-dev` commit `1b1c28bc2a18d70e6b5cec23c6f7bc869e24f51f`
- Completion baseline: `v7-dev` commit `1daff9e58bd52058e44175c99b4248ea321a30f5`
- Prerequisite: V7-13 Private Panel-Aware Page Generation Foundation is complete
- Public activation: disabled; HTTP/Web/Application activation remains V7-15+

## Completion Evidence

V7-14 is complete across Slices 1–3. GitHub records confirm the merged PRs,
merge commits, and PR-head CI checks listed below. The final independent review
is recorded in the Codex task `slice3_final_review`.

| Slice | Pull request | PR head | Merge commit | PR-head CI |
| --- | --- | --- | --- | --- |
| 1 — deterministic converter | [#61](https://github.com/esuforesuto-cmd/manga-director-oss/pull/61) | `cd125b550b55ff016a737a8e2e022c02196e6f9c` | `c9b0c27ef1df8104f70b573c9dd7c10266b523df` | 24/24 succeeded |
| 2 — private ComfyUI adapter | [#62](https://github.com/esuforesuto-cmd/manga-director-oss/pull/62) | `133d3c17860817a37e5fe66b489b46469104b3c9` | `4feeae65cab5a48397f274164422588d4e2f7adc` | 24/24 succeeded |
| 3 — operation composition | [#63](https://github.com/esuforesuto-cmd/manga-director-oss/pull/63) | `383c94ec3c14f67b48aed4ac484dfd81d6326d26` | `1daff9e58bd52058e44175c99b4248ea321a30f5` | 24/24 succeeded |

The `slice3_final_review` record reports P0 = 0, P1 = 0, and P2 = 0 for the
completed Slice 3 diff. CI counts
above are for the respective PR heads; no post-merge CI result is claimed. The
three slices changed the seven unique implementation/test files listed below.
No live ComfyUI call, I02 action, `main` change, release or publication,
dependency/lockfile change, schema/migration change, or branch deletion was
performed or authorized by V7-14. The feature branches remain present.

## Title

V7-14 — Safe Panel-Aware Activation Bridge

## Objectives

Design and implement a private, deterministic bridge that converts the existing
persisted LocalFile `Storyboard` and `PromptBuilt` artifacts to the already
frozen private `PageGenerationPlan`, and adapt the V7-13
`PanelProviderExecutionPort` to the existing V7-04
`ComfyUIImagePrivateTransport`. The bridge must use V7-13 orchestration and
durable authorities without introducing another activation or persistence
authority. Implementation is complete under the separately approved V7-14
Slice 1–3 scopes recorded in Completion Evidence.

## Scope

The implemented slices are private and LocalFile-only. They cover exact
source-artifact conversion, plan/request binding, private provider adaptation,
and composition with existing V7-13 authorities. It does not add a public
activation route or change existing workflow entry points.

### A. Deterministic persisted-artifact converter

The converter reads one authoritative, revisioned LocalFile Page snapshot and
the exact persisted `Page.storyboard` and `Page.prompt` dict artifacts for that
Page. These fields are plain dictionaries and expose no stable artifact
reference fields. The bridge derives safe references from their canonical
content digests. Their references/digests and the authoritative page revision
and fingerprint enter the `source_binding_v1` digest that determines `plan_id`;
the frozen `PageGenerationPlan` itself has no revision or page-fingerprint
fields. The mode claim and operation bind their respective snapshot values
directly: the claim binds revision and page fingerprint, and the operation
binds revision. Both artifacts must come from the same snapshot; mutable or
unbound reads and artifact rewriting are forbidden.

The converter uses this closed mapping. It does not rename, concatenate,
summarize, reinterpret, or substitute unlisted Storyboard values:

| Persisted source | V7-13 plan field | Rule |
| --- | --- | --- |
| Storyboard `number` | `PagePanelSpecification.order` | Require a strict integer sequence `1..N` in persisted order; reject booleans, gaps, duplicates, or reordering. |
| Derived panel reference (see “Canonical derivation rules”) | `PagePanelSpecification.panel_id` | Derived deterministically from the full source binding and the exact order because current Storyboard has no explicit panel ID. Never use role/name as identity. |
| Existing explicit `narrative_intent` extension, if persisted | `narrative_intent` | Require it explicitly; current Storyboard does not provide it. `role` is not a substitute. |
| Storyboard `characters` | `character_identities` | Require a nonempty ordered list of explicit stable identities; reject generic/abstract values such as `protagonist`; preserve order and exact trimmed strings. |
| Existing explicit `continuity_bindings` extension, if persisted | `continuity_bindings` | Require it explicitly; current Storyboard does not provide it. Do not infer from character, expression, prior panels, or dialogue. |
| Storyboard `action` | `action` | Require pre-existing explicit concrete text. Do not infer or repair it. |
| Storyboard `background` | `background` | Require pre-existing explicit concrete text. |
| Storyboard `composition` | `composition` | Require pre-existing explicit concrete text. |
| Existing explicit `constraints` extension, if persisted | `constraints` | Require a nonempty ordered list of explicit concrete constraints; current Storyboard does not provide it. |
| Exact separately persisted supported layout input | `rectangle` and plan layout profile | Require exact supported profile/version and one valid rectangle per panel/order. Current Storyboard does not provide these values. |

All other current Storyboard fields—`role`, `camera`, `expression`,
`dialogue`, `sound_effect`, and `balloon_position`—have no destination in the
frozen plan contract and are not folded into a prompt field or used to fill a
missing field. Current Storyboard therefore lacks explicit `panel_id`,
`rectangle` and layout profile, `narrative_intent`, `continuity_bindings`, and
`constraints`. The absent `panel_id` is deterministically derived as specified
in the mapping and is not an explicit-source precondition. Missing rectangles,
layout profile, narrative intent, continuity bindings, or constraints are
fail-closed unless exact explicit values are already present in approved
persisted inputs. No upstream schema change is authorized here.

Plan-level fields are equally closed: `project_id`, `page_id`, and
`page_number` come from the same authoritative snapshot. `page_number` is the
positive `Page.page_number` persisted in that snapshot. `page_id` is derived
from that same integer as its canonical base-10 ASCII representation with no
leading zeroes; it is not an independent input. Reject any separately supplied
`page_id` or alias representation such as `"01"` rather than normalizing or
accepting it. This derivation produces the same identifier as the existing
`LocalFilePageGenerationModeObservation.observe` normalization
`str(int(page_id))`, but the bridge must not rely on that normalization to make
an alias admissible. Safe
`storyboard_reference` and `prompt_built_reference` are bridge-derived from
their respective full content digests below, not preserved artifact metadata;
their hashes use the same digests. `plan_id` is derived below from a binding
that also contains the snapshot revision and page fingerprint; neither
revision nor page fingerprint is a `PageGenerationPlan` field.
`PageGenerationModeClaim` directly binds page revision and page fingerprint;
`PanelAwarePageGenerationOperation` directly binds page revision. `panel_count`
is the number of validated, ordered panels; plan/profile versions, canvas
size, margins, and gutter come only from the frozen V7-13 constants. The
canonical plan fingerprint is computed by the existing V7-13 model validator.
No field is sourced from process environment, PromptBuilt prose, another
revision, or a generated fallback.

Two user-highlighted gaps remain explicit hard stops:

- `StoryboardAgent` currently defaults `action` to `advance the page purpose`,
  which the concrete `PagePanelSpecification` prompt contract rejects as
  abstract. Require a pre-existing explicit concrete action; never infer,
  rewrite, or auto-fill it from dialogue, role, narrative intent, an LLM, or
  another field.
- Existing Storyboard data has no panel rectangles. Require an exact supported
  layout input with valid geometry for every panel. Never derive a grid, choose
  a layout, estimate rectangles, or auto-fill geometry. Missing, unsupported,
  malformed, overlapping, or invalid layout blocks conversion.

The existing StoryboardAgent also defaults `characters` to `protagonist`,
which is rejected by the concrete identity contract. Require explicit stable
character identity values; do not replace generic values with names or infer
identity from other artifacts.

The frozen V7-13 layout profile remains authoritative: 2048 by 3072 canvas,
normalized integer rectangle coordinates using its integer floor rule, minimum
margins and gutter, and bounded panel count. A candidate layout input must
identify the exact supported profile/version and provide explicit rectangles
in panel order. This RFC adds no layout schema and persists no layout data.

`Page.prompt` is the persisted PromptBuilt artifact dictionary and must contain
the exact `prompt_markdown` string. Its full dictionary is bound by canonical
digest and a derived safe reference; the Markdown is never parsed, split, or
treated as a source for per-panel fields, layout, identity, or prompt repair.

### Closed canonical derivation rules

Canonical serialization for every object below is UTF-8 JSON using
`ensure_ascii=False`, sorted object keys, compact separators `,` and `:`, and
no trailing newline. Arrays keep the order stated below. A digest is full
lowercase SHA-256 hex (64 characters) over those canonical bytes; a derived
logical reference is its exact ASCII prefix followed by the full digest. Never
truncate a digest or concatenate unlabelled values to make a preimage.

### Ordered derivation

1. From one immutable revisioned snapshot, take the full `Page.storyboard` and
   `Page.prompt` dictionaries. Require `Page.prompt["prompt_markdown"]` to be a
   string. Hash each complete dictionary using the canonical JSON rule above.
   This binds the exact Markdown string and metadata; do not parse Markdown for
   panel data. Derive `storyboard_reference` as
   `storyboard-v7-014-<storyboard_sha256>` and `prompt_built_reference` as
   `prompt-v7-014-<prompt_built_sha256>`. They are bridge-owned content refs,
   not persisted artifact IDs.
2. Construct exactly one `source_binding_v1` object. Its literal keys, nested
   shapes, and value types are:

   ```json
   {
     "kind": "source_binding_v1",
     "version": 1,
     "project_id": "<safe string>",
     "page_id": "<safe string>",
     "page_number": 1,
     "page_revision": "<safe revision string>",
     "page_fingerprint": "<64 lowercase hex>",
     "storyboard_reference": "<derived safe string>",
     "storyboard_sha256": "<64 lowercase hex>",
     "prompt_built_reference": "<derived safe string>",
     "prompt_built_sha256": "<64 lowercase hex>",
     "layout": {
       "profile_id": "md-page-compositor-v1",
       "profile_version": 1,
       "canvas_width": 2048,
       "canvas_height": 3072,
       "margins": [96, 96, 96, 96],
       "gutter_px": 48
     },
     "panels": [
       {
         "number": 1,
         "narrative_intent": "<explicit string>",
         "character_identities": ["<explicit string>"],
         "continuity_bindings": ["<explicit string>"],
         "action": "<explicit string>",
         "background": "<explicit string>",
         "composition": "<explicit string>",
         "constraints": ["<explicit string>"],
         "rectangle": {
           "left": 0,
           "top": 0,
           "right": 1000000,
           "bottom": 1000000
         }
       }
     ]
   }
   ```

   The panel array is in persisted Storyboard order and every `number` must
   equal its 1-based array position. `margins` are ordered `(top, right,
   bottom, left)` exactly as V7-13 geometry validation expects. Values shown
   as placeholders are typed
   strings, integer coordinates, or ordered string arrays exactly as shown;
   the example rectangle is illustrative only and must still pass V7-13
   geometry validation. `page_fingerprint` and `page_revision` are observed
   from the same authoritative snapshot. Hash this entire object canonically
   to obtain `source_binding_sha256`.
3. Derive `plan_id` as
   `plan-v7-014-<source_binding_sha256>`. This is the only route by which
   revision/page fingerprint participate in plan identity: the frozen
   `PageGenerationPlan` DTO has no revision or page-fingerprint fields. Bind
   revision and page fingerprint directly in `PageGenerationModeClaim`, and
   revision directly in `PanelAwarePageGenerationOperation`; both must use the
   same snapshot and pass existing admission/recheck gates. The existing PageGenerationPlan
   validator computes `plan_fingerprint` after plan construction.
4. For each ordered source panel derive `panel_id` from this exact object:
   `{"kind":"panel_id_v1","version":1,"source_binding_sha256":"<64hex>","panel_order":1}`.
   Hash canonically and prefix the full digest with `panel-v7-014-`. Use that
   ID and the ordered source panel to construct the immutable
   `PagePanelSpecification`; then construct `PageGenerationPlan` and let its
   existing validator compute the fingerprint. No ID depends on a later
   fingerprint, so there is no circular derivation.
5. Define `raw_prompt_object_v1` as exactly this JSON object, containing only
   the seven mapped textual fields and preserving array order:

   ```json
   {
     "action": "<string>",
     "background": "<string>",
     "character_identities": ["<string>"],
     "composition": "<string>",
     "constraints": ["<string>"],
     "continuity_bindings": ["<string>"],
     "narrative_intent": "<string>"
   }
   ```

   Canonically serialize `raw_prompt_object_v1` once. The resulting Unicode
   JSON text, without a trailing newline, is the exact `raw_prompt` string
   passed to `ProviderPrivateTransportRequest`; its UTF-8 encoding is the exact
   byte sequence hashed for `input_sha256`. Derive `input_reference` as
   `input-v7-014-<input_sha256>`. No other JSON object, Markdown text, or
   re-serialization may be used for either value.

   Separately, the canonical `PagePanelSpecification` JSON object embedded as
   `panel_prompt` in `PanelGenerationRequest` has exactly these keys and value
   types:

   ```json
   {
     "panel_id": "<derived safe string>",
     "order": 1,
     "rectangle": {
       "left": 0,
       "top": 0,
       "right": 1000000,
       "bottom": 1000000
     },
     "narrative_intent": "<string>",
     "character_identities": ["<string>"],
     "continuity_bindings": ["<string>"],
     "action": "<string>",
     "background": "<string>",
     "composition": "<string>",
     "constraints": ["<string>"]
   }
   ```

   This second object is never the transport `raw_prompt` preimage. Its
   `panel_id`, order, and rectangle remain request binding/composition metadata
   and are not prompt content. Its seven textual values must equal the
   corresponding values in `raw_prompt_object_v1`; any difference blocks the
   request.
6. Freeze `capability_requirements` as the exact ordered tuple
   `("text-prompt", "png-output")`. Derive `provenance_reference` by
   canonically hashing exactly
   `{"kind":"panel_provenance_v1","version":1,"source_binding_sha256":"<64hex>","plan_id":"<safe string>","plan_fingerprint":"<64hex>","panel_id":"<safe string>","panel_order":1}`
   and prefixing `panel-provenance-v7-014-`. Derive `request_id` by hashing
   exactly this object (excluding the derived `request_id` and model-computed
   `request_fingerprint`):

   ```json
   {
     "kind": "panel_request_v1",
     "version": 1,
     "plan_id": "<safe string>",
     "plan_fingerprint": "<64 lowercase hex>",
     "project_id": "<safe string>",
     "page_id": "<safe string>",
     "panel_id": "<safe string>",
     "panel_order": 1,
     "panel_prompt": {
       "panel_id": "<derived safe string>",
       "order": 1,
       "rectangle": {
         "left": 0,
         "top": 0,
         "right": 1000000,
         "bottom": 1000000
       },
       "narrative_intent": "<string>",
       "character_identities": ["<string>"],
       "continuity_bindings": ["<string>"],
       "action": "<string>",
       "background": "<string>",
       "composition": "<string>",
       "constraints": ["<string>"]
     },
     "capability_requirements": ["text-prompt", "png-output"],
     "input_reference": "<derived safe string>",
     "input_sha256": "<64 lowercase hex>",
     "provenance_reference": "<derived safe string>"
   }
   ```

   Prefix the full digest with `request-v7-014-`. Construct the existing
   `PanelGenerationRequest`; its validator computes `request_fingerprint`.
7. Require an already-issued safe `authorization_reference` independent of the
   not-yet-derived attempt ID. If it is unavailable or depends on that ID, fail
   closed. Derive `attempt_id` by hashing exactly
   `{"kind":"panel_attempt_v1","version":1,"request_fingerprint":"<64hex>","provider_reference":"provider-comfyui-v7-014","authorization_reference":"<safe authority-issued string>"}`
   and prefixing `attempt-v7-014-`. No provider configuration fingerprint is
   an input to this ID.
8. Construct the private provider selection and output binding for this
   `attempt_id` and fixed provider reference. Require `provider_id` to equal
   `comfyui`, a validated checkpoint/model ID, model version
   `local-checkpoint`, profile ID `profile:v7-04:prompt-only-png`, profile
   version `v1`, workflow ID `workflow:v7-04:fixed-core-png`, workflow version
   `v1`, null `preset_id` and `preset_version`, requested seed evidence
   `derived-from-attempt`, and the fixed output values. Then derive
   `provider_configuration_fingerprint` from exactly
   `{"kind":"provider_configuration_v1","version":1,"attempt_id":"<safe string>","provider_reference":"provider-comfyui-v7-014","provider_id":"comfyui","model_id":"<validated safe checkpoint string>","model_version":"local-checkpoint","profile_id":"profile:v7-04:prompt-only-png","profile_version":"v1","workflow_id":"workflow:v7-04:fixed-core-png","workflow_version":"v1","preset_id":null,"preset_version":null,"requested_seed":"derived-from-attempt","output_size":"1024x1024","output_quality":"medium"}`.
   Validate profile/workflow values under their own provider contracts, not the
   V7-13 logical-reference regex. The checkpoint/model ID must pass the V7-04
   validator and match exactly across selection, output binding, and transport;
   all fixed values above must match. If a required value is unavailable or a
   binding differs, fail closed.
9. Derive `execution_fingerprint` by hashing exactly
   `{"kind":"panel_execution_v1","version":1,"attempt_id":"<safe string>","request_fingerprint":"<64hex>","provider_reference":"provider-comfyui-v7-014","authorization_reference":"<safe authority-issued string>","provider_configuration_fingerprint":"<64hex>"}`.
   This order is acyclic: request fingerprint precedes attempt ID; attempt ID
   precedes private provider selection and configuration fingerprint; the
   execution fingerprint is last.
10. Before provider invocation, derive the IDs used by a successful
    `PanelProviderExecution` from the already-frozen execution binding. Derive
    `asset_id` by hashing exactly
    `{"kind":"panel_asset_id_v1","version":1,"attempt_id":"<safe string>","request_fingerprint":"<64hex>","execution_fingerprint":"<64hex>","input_sha256":"<64hex>","provider_configuration_fingerprint":"<64hex>","provenance_reference":"<safe string>","media_type":"image/png"}`
    and prefixing `panel-asset-v7-014-`. Derive `evidence_id` by hashing exactly
    `{"kind":"panel_evidence_id_v1","version":1,"attempt_id":"<safe string>","request_fingerprint":"<64hex>","execution_fingerprint":"<64hex>","asset_id":"<safe string>"}`
    and prefixing `panel-evidence-v7-014-`. These IDs are consumed only for a
    successful result. The returned `PanelAsset` and
    `PanelGenerationEvidence` must bind those exact IDs, request/attempt values,
    provider/configuration/provenance values, PNG media type, and the actual
    output digest and dimensions; a declared failure returns neither object,
    and an uncertain result is `RECOVERY_REQUIRED`.
11. Require an already-issued safe
    `composition_authorization_reference` independent of every composition ID.
    The frozen `PanelAwarePageGenerationOperation` has no standalone
    `operation_id` field. Its composition-operation identity is the existing
    `composition_attempt_id`; throughout this RFC, "operation ID" means that
    exact field, and the bridge must not invent an additional or alias ID.
    Derive `composition_provenance_reference` by hashing exactly
    `{"kind":"composition_provenance_v1","version":1,"source_binding_sha256":"<64hex>","plan_id":"<safe string>","plan_fingerprint":"<64hex>","ordered_request_fingerprints":["<64hex>"],"ordered_attempt_ids":["<safe string>"]}`
    and prefixing `composition-provenance-v7-014-`. The two arrays use panel
    order and must contain exactly the complete plan panel set. Derive
    `composition_attempt_id` by hashing exactly
    `{"kind":"composition_attempt_v1","version":1,"plan_id":"<safe string>","plan_fingerprint":"<64hex>","page_revision":"<safe revision string>","composition_authorization_reference":"<safe authority-issued string>","composition_provenance_reference":"<safe string>","compositor_profile_id":"md-page-compositor-v1","compositor_profile_version":1,"ordered_request_fingerprints":["<64hex>"],"ordered_attempt_ids":["<safe string>"]}`
    and prefixing `composition-attempt-v7-014-`. From that exact attempt ID,
    derive the remaining `PanelAwarePageGenerationOperation` IDs by hashing
    these exact objects:

    - `composition_evidence_id`:
      `{"kind":"composition_evidence_id_v1","version":1,"composition_attempt_id":"<safe string>","plan_id":"<safe string>","plan_fingerprint":"<64hex>"}`,
      prefixed `composition-evidence-v7-014-`;
    - `composite_asset_id`:
      `{"kind":"composite_asset_id_v1","version":1,"composition_attempt_id":"<safe string>","plan_id":"<safe string>","plan_fingerprint":"<64hex>","media_type":"image/png"}`,
      prefixed `composite-asset-v7-014-`; and
    - `application_id`:
      `{"kind":"composition_application_id_v1","version":1,"composition_attempt_id":"<safe string>","plan_id":"<safe string>","plan_fingerprint":"<64hex>","project_id":"<safe string>","page_id":"<safe string>","page_revision":"<safe revision string>"}`,
      prefixed `composition-application-v7-014-`.

    These IDs are fixed before panel provider side effects. The later
    `PageCompositionRequest.request_fingerprint`, panel output hashes, composite
    hash, composition evidence, and application binding remain authoritative
    content bindings under the existing V7-13 validators; they are not inputs
    to the predeclared IDs. Any mismatch fails closed. This completes every
    bridge-owned ID required by `PanelProviderExecution` and
    `PanelAwarePageGenerationOperation` without a cycle.
12. Project ID, Page ID, revision, derived refs, IDs, provider reference, and
    authority-issued V7-13 logical references must match
    `[A-Za-z0-9][A-Za-z0-9._-]{0,127}` and reject secret/token/credential
    markers. Serialize revision exactly as `revision-` plus the snapshot's
    base-10 revision number without padding. Page number is a strict positive
    integer (booleans are invalid). Colons, whitespace,
    paths, and endpoint strings are invalid in those logical references.
    Preserve safe project/Page/revision/authority-owned refs exactly; use only
    `provider-comfyui-v7-014` as this bridge's provider ref. Profile/workflow
    identifiers use their own validators. Never derive an ID from credentials
    or secret values; fail closed if any required binding is unavailable.

### B. Private V7-13-to-V7-04 provider adapter

The adapter implements private V7-13 `PanelProviderExecutionPort` and a
private preparatory subprotocol. For each operation it receives one exact
`PanelGenerationRequest` and durable `PanelAttemptReservation`; it verifies
plan and request fingerprints, Page, panel identity/order, prompt, provider,
authorization, and execution bindings. It maps that one panel's explicit
concrete prompt into the existing provider-neutral invocation composition and
V7-04 private ComfyUI transport request.

Reuse existing provider configuration and output-configuration validation,
the exact bound invocation adapter, `ComfyUIImagePrivateTransport`, fixed
ComfyUI graph, and safe PNG output registration/evidence path where applicable.
Do not add another ComfyUI client, graph, free-form endpoint, prompt fallback,
alternate provider, retry, or fallback behavior. Provider request/response
details, prompt material, image bytes, and opaque runtime handles remain
private and are never serialized into durable reports or public results.

V7-04's existing LocalFile composition uses `_PROVIDER_REFERENCE =
"provider:comfyui"`; its colon is invalid for V7-13 `logical_reference` and
cannot be copied into `PanelAttemptReservation.provider_reference`. The bridge
uses the one fixed safe private value `provider-comfyui-v7-014` for the V7-13
reservation and for the private V7-04 `ProviderConfigurationSelectionDTO`,
`ProviderOutputConfigurationBindingDTO`, and transport request. Their
provider-reference bindings must match this exact value. The selected
`provider_id` remains the existing ComfyUI identity required by the transport.
Do not change the V7-04 constant, legacy configuration, or any public contract.

Provider profile IDs such as `profile:v7-04:prompt-only-png` and workflow IDs
such as `workflow:v7-04:fixed-core-png` are governed by their existing
provider-configuration, evidence-value, and fixed-workflow validators. Preserve
and validate them under those contracts; do not incorrectly apply the stricter
V7-13 `logical_reference` regex or rewrite them to remove colons.

Freeze this two-phase sequence for the V7-14 ComfyUI adapter:

1. V7-13 mode admission succeeds for the exact Page revision.
2. The existing panel authority durably reserves the exact attempt.
3. An optional private preparatory panel-provider subprotocol is detected.
   Only its implementation may run bounded, read-only ComfyUI preflight and
   `ComfyUIImagePrivateTransport.prepare`; preparation must not POST, poll, or
   fetch generated output. It returns a short-lived, non-serializable prepared
   callable bound to the exact request and reservation. No user prompt,
   generated bytes, or opaque runtime handle is persisted.
4. If preflight or preparation fails, return blocked with the attempt still
   `RESERVED`; do not record provider-start, invoke the legacy `invoke` path,
   or submit. A later explicit operation may repeat bounded read-only
   preflight/preparation only when the authoritative lookup returns the exact
   same `PanelAttemptReservation`, its state is still `RESERVED`, and
   `provider_start_consumed` is false. Reuse that same reservation and durable
   attempt; do not reserve or create a new attempt. A request-binding or
   reservation mismatch, any state other than `RESERVED`, or a consumed
   provider-start opportunity forbids re-preparation and follows the existing
   accepted, blocked, or recovery-required semantics as applicable.
5. Recheck the Page/mode authority and durably record provider-start using the
   existing `run_provider_start_admitted` boundary. This recheck occurs after
   preparation and immediately before start.
6. Only after durable start succeeds, call the prepared callable exactly once.
   Any exception, lost result, or uncertain submit after start uses existing
   `RECOVERY_REQUIRED`; never declare preparation failure after start, retry,
   or fall back.

The existing `PanelProviderExecutionPort.invoke` contract remains unchanged.
The orchestrator may recognize an optional/private preparatory subprotocol
implemented by the ComfyUI adapter. Existing simple fake providers that do not
implement it retain the current post-start `invoke` sequence for compatibility.
The ComfyUI adapter must require preparation; it must never fall back to direct
post-start `invoke` if its preflight or preparation fails. This keeps its
network submission behind durable start while moving all known fallible
read-only preparation ahead of that durable one-shot boundary.

The V7-14 orchestrator routes every confirmed non-accepted existing attempt
to recovery before provider invocation, except for the narrow exact-`RESERVED`
reuse case above; that case is handled before the generic recovery path. All
mismatched and non-`RESERVED` existing-attempt behavior remains unchanged.

## Inputs

- Completed V7-13 private plan, panel-attempt, evidence, orchestration,
  composition, mode-admission, and recovery contracts.
- One revisioned LocalFile Page snapshot containing the exact persisted
  `Page.storyboard` and `Page.prompt` dict artifacts and content; the bridge
  derives logical source references from the full canonical content digests
  because these fields expose no stable artifact references.
- A pre-existing explicit concrete action for every panel.
- An exact already-supported layout input with explicit geometry for every
  panel under the frozen V7-13 profile.
- Existing ComfyUI provider identity, configuration/output-configuration
  prerequisites, and V7-04 fixed-graph/private transport requirements. The
  private V7-13/V7-04 binding uses the fixed safe bridge-local provider
  reference defined above.
- Existing V7-13 durable mode claim, admission fence, panel reservation,
  authorization, and execution bindings.

Absent, ambiguous, stale, unsupported, mismatched, or invalid input blocks
conversion or invocation with no inferred replacement.

## Outputs

- A deterministic private `PageGenerationPlan` bound to the exact persisted
  source artifacts by their derived safe references and full content digests,
  plus the V7-13 canonical plan fingerprint.
- One exact `PanelGenerationRequest` and matching reservation per panel in
  canonical order, passed to existing V7-13 orchestration.
- Private `PanelProviderExecution` results and existing V7-13 durable panel
  assets/evidence/composition proof, only when existing authorities accept the
  exact bindings.
- Existing private blocked or recovery-required results; no new public result
  contract.

## Acceptance Criteria

1. Identical authoritative snapshot content and supported explicit layout
   input produce identical canonical plan content and fingerprint. A change to
   source content, reference, revision, or layout changes its binding or fails
   closed.
2. Conversion requires exact Storyboard and PromptBuilt artifacts from one
   authoritative snapshot and binds both references and SHA-256 digests.
3. The abstract/default action `advance the page purpose`, a missing explicit
   concrete action, or any other rejected prompt value blocks conversion. No
   path infers or fills the action.
4. Missing panel rectangles or missing/unsupported layout input blocks
   conversion. No geometry is invented, estimated, selected, or auto-filled.
5. Existing V7-13 validators enforce panel identity/order/count, concrete
   prompts, plan fingerprint, supported profile, margins, gutters, bounds,
   non-overlap, and deterministic geometry.
6. Legacy single-canvas and panel-aware modes remain mutually exclusive under
   existing durable mode admission. The ComfyUI adapter follows the frozen
   sequence: admission, durable reservation, read-only preflight/prepare with
   no POST, authority recheck and durable provider-start, then one prepared
   submit. No provider submission occurs before the durable start.
7. Each reserved panel submits at most once. Restart after an ambiguous
   provider-start fails closed into existing recovery-required handling and
   does not resubmit automatically.
8. Preflight or preparation failure leaves the attempt `RESERVED`, with no
   provider-start or POST. A later explicit operation may re-run only bounded
   read-only preflight/preparation by reusing the same exact reservation when
   its authoritative record remains `RESERVED` and provider-start is
   unconsumed. Binding mismatch, reservation mismatch, any non-`RESERVED`
   state, or consumed provider-start forbids re-preparation and cannot create a
   replacement attempt. Any exception or uncertain outcome after durable start
   is recovery-required; it is never reclassified as preparation failure.
9. Exact request, reservation, provider configuration, authorization,
   execution, output asset, evidence, composition, and Page bindings are
   checked end to end; mismatched evidence is rejected.
10. The adapter uses existing V7-04 fixed-graph/private-transport and
   validation boundaries. No second client, graph, retry, provider fallback,
   or alternate endpoint is introduced.
11. HTTP/Web/Application public activation remains disabled for V7-14 and is
    deferred to V7-15 or later. Existing public `ComfyUIImageGenerator`
    remains an API-boundary stub.
12. No I02, schema/migration, dependency/lockfile, public API, release, `main`,
    publication, or unrelated implementation change is included.
13. Satisfied: implementation started only after review and explicit user
    approval of separate exact implementation allowlists and validation plans
    for Slices 1–3; see Completion Evidence.
14. Focused tests pin literal canonical JSON bytes and golden full-SHA256
    vectors for source dicts/references, `source_binding_v1`, plan/panel IDs,
    raw prompt/input binding, panel provenance/request ID and request
    fingerprint, panel attempt ID, provider-configuration and execution
    fingerprints, panel asset/evidence IDs, composition provenance/attempt/
    evidence IDs, composite asset ID, and composition application ID.
    The vectors prove array ordering, sorted object keys, full digest lengths,
    and the acyclic dependency order. Page revision/fingerprint are in the
    source binding and claim; revision is also direct on the operation. Tests
    do not expect new revision fields on `PageGenerationPlan`.

## Out of Scope

- Further implementation beyond the completed private V7-14 scope; changes to
  configuration, dependencies, lockfiles, schemas, migrations, exports, or
  public APIs.
- HTTP, Web, Application, CLI, MCP, SDK, Plugin, or any other public
  activation. Public activation is V7-15+ and needs its own approved design.
- Changing StoryboardAgent defaults or adding LLM repair/enrichment.
- Creating, inferring, selecting, or persisting layout/rectangle data or adding
  a layout schema.
- Changes to V7-13 durable authorities, V7-04 transport/security/fixed graph,
  public `ComfyUIImageGenerator` stub, legacy generation, or mode admission.
- Live ComfyUI/provider calls, I02, release, `main`, dependencies/lockfiles,
  package publication, tags, PR, merge, or branch operations.
- Automatic retries, provider switching, fallback, concurrency, or another
  persistence authority.

## Dependencies

- V7-13 remains complete with public routing disabled and unchanged durable
  mode-admission, panel attempt, evidence, asset, recovery, deterministic
  composition, and output-proof authorities.
- V7-04 remains the only ComfyUI private transport path, including its
  preflight, fixed graph, bounded loopback transport, one-shot invocation, and
  strict output handling.
- V7-03 provider-neutral invocation composition and existing V7-04
  configuration/output binding remain the adapter boundary.
- Persisted source artifacts must already contain explicit concrete panel
  actions and exact supported layout input before a private V7-14 Page
  generation operation can proceed. This RFC does not authorize changing
  upstream artifact production to fill either gap.

## Validation

Slices 1–3 passed the recorded PR-head CI checks listed in Completion Evidence,
with 24/24 checks succeeding for each PR. The Codex task record
`slice3_final_review` reports P0 = 0, P1 = 0, and P2 = 0. Direct live ComfyUI
calls were not made. These are PR-head results; no post-merge CI result is
claimed. This closure update is limited to the two documentation files listed
below.

Any future implementation proposal must include focused tests for deterministic
conversion and artifact binding; every closed source mapping and missing-field
failure; exact layout geometry; mode exclusion; read-only prepare before
durable start; post-prepare authority recheck; prepare-failure `RESERVED`
semantics; successful re-preparation using the same exact `RESERVED`
reservation with unconsumed provider-start; rejection of request-binding or
reservation mismatch, non-`RESERVED` state, and consumed provider-start;
proof that no retry path creates a new attempt; submit-after-start ordering;
at-most-once/restart recovery; evidence
binding; prompt rendering; disabled public routing; and the literal canonical
JSON/golden-digest vectors required by Acceptance Criterion 14. The vectors
must test every preimage and derived reference independently, including the
existing model-computed plan/request fingerprints. Pin expected canonical JSON
bytes and full SHA-256 values as literals, not as outputs recomputed by the
same helper under test. Assert that page revision and page fingerprint bind
through `source_binding_v1` to `plan_id`, while the mode claim binds both
directly and the operation binds revision directly; do not add fields to
`PageGenerationPlan`. It must then run applicable tests,
regression checks, lint, typecheck, security/audit, and `git diff --check` under
its newly approved allowlist. Tests cannot authorize live ComfyUI, I02,
release, or public activation.

## Estimated Complexity

High. The closed conversion and ID rules are deterministic, but source
completeness and the prepare/recheck/start/submit choreography cross several
existing private authorities. Current Storyboard output lacks multiple
required plan fields and layout data; ordinary output is expected to block
until all exact inputs already exist.

## Architecture Notes

- Keep the bridge private and composition-based. Conversion creates no
  authority; V7-13 remains authoritative for mode admission, attempts,
  durable provider-start, evidence, assets, recovery, composition, and proof.
- Preserve mutual exclusion between legacy and panel-aware generation for a
  Page.
- Add a private optional preparatory subprotocol without changing the existing
  `PanelProviderExecutionPort.invoke` contract. After mode admission and
  durable reservation, ComfyUI preflight and transport `prepare` are bounded
  read-only operations with no POST. On success, recheck the exact Page/mode
  authority and durably record provider-start, then invoke the prepared
  callable once. Preparation failure leaves the attempt `RESERVED` and blocked;
  only the exact same `RESERVED` reservation with unconsumed provider-start may
  repeat bounded read-only preparation. The V7-14 orchestrator distinguishes
  that narrow case from its current generic recovery handling for confirmed
  existing attempts. After start, every uncertain outcome is recovery-required.
  Never fall back from preparatory ComfyUI to ordinary `invoke`.
  Non-preparatory test fakes retain the current start-then-invoke behavior.
- Bind source references/digests, plan/request fingerprints, reservations,
  authorization, provider configuration, evidence, assets, composition, and
  Page revision. Any mismatch fails closed.
- An ambiguous started attempt is recovery-required after restart. Never
  resubmit, retry, or switch providers.
- Keep `ComfyUIImagePrivateTransport` and its fixed-graph security behavior as
  the sole ComfyUI transport. Do not duplicate transport or expose provider
  details.
- Public routing remains disabled; public `ComfyUIImageGenerator` remains a
  stub. HTTP/Web/Application activation belongs to V7-15+.
- Explicit concrete action and supported exact layout input are preconditions,
  never inferred outputs.

## Exact documentation allowlist for this V7-14 closure record

1. `docs/RFC_V7_012_SAFE_PANEL_AWARE_ACTIVATION_BRIDGE.md`
2. `docs/ROADMAP_V7.md`

No other file is in scope.

## Completed V7-14 implementation file set

The approved Slices 1–3 changed exactly these seven unique files:

1. `src/manga_director/workflow/localfile_panel_aware_activation_bridge.py` —
   private snapshot-bound converter and operation composition.
2. `src/manga_director/workflow/localfile_comfyui_panel_provider.py` — private
   `PanelProviderExecutionPort` adapter composed over existing V7-03/V7-04
   boundaries.
3. `src/manga_director/workflow/localfile_panel_aware_page_generation.py` —
   recognize the optional/private preparatory subprotocol while retaining the
   existing `invoke` contract; order prepare, authority recheck, durable start,
   and one prepared invocation.
4. `tests/test_localfile_panel_aware_activation_bridge.py` — deterministic
   conversion and fail-closed input/binding coverage.
5. `tests/test_localfile_comfyui_panel_provider.py` — adapter binding,
   preflight/prepare without POST, and prepared-call behavior using fakes only.
6. `tests/test_localfile_panel_aware_page_generation.py` — focused coverage for
   preparatory and existing simple fake providers, RESERVED preparation
   failure, same-exact-reservation preparation retry, mismatch and
   non-RESERVED retry rejection, post-prepare authority recheck,
   start-before-submit, and recovery-required handling after uncertain
   post-start outcome.
7. `tests/test_localfile_panel_aware_page_generation_activation.py` — narrow
   private composition coverage proving V7-13 authorities and disabled public
   routing remain in force.

If implementation requires any additional file, especially an existing
authority, public route, Page schema, migration, configuration/dependency,
lockfile, export, or public API, stop and submit a revised scope and allowlist
for explicit approval before editing it.

## STOP conditions

Stop before admission or provider activity if any required mapped source field
is missing, including the highlighted explicit concrete action and exact
supported layout input. Also stop on a stale or mixed snapshot,
missing/ambiguous artifact identity, invalid or unsupported geometry, prompt
validation failure, unsafe logical reference, binding/fingerprint mismatch,
mode conflict, or non-durable admission/reservation. ComfyUI preflight or
prepare failure leaves the attempt `RESERVED` and blocked with no
provider-start or POST. Re-preparation stops unless authoritative lookup proves
the same exact reservation is still `RESERVED` with provider-start unconsumed;
never replace it with a new attempt. If authority recheck/start fails, do not
invoke the prepared callable. After durable start, any exception or uncertain
submit is recovery-required; never retry, misclassify it as preparation
failure, fall back, or switch providers.

Stop any follow-up implementation and seek new explicit approval if it needs
files outside the completed V7-14 implementation set or affects public routing,
schema/migration, dependencies/lockfiles, public API, V7-13/V7-04 authorities,
I02, live ComfyUI, release, `main`, or publication.

## Authorization Gate

V7-14 implementation is complete only within the delivered private scope and
the separately approved Slice 1–3 allowlists. This closure does not authorize
follow-up implementation or expand any scope. Public HTTP/Web/Application
activation remains V7-15+ and requires a separate design and explicit
authorization. Live ComfyUI, I02, `main`, release/publication,
dependency/lockfile, schema/migration, and branch deletion remain unperformed
and unapproved. Any follow-up work requires its own explicit approval.

## Asset-ID Registration Contract Amendment (2026-10-28)

Status: implemented and verified as V7-15 Slice 1 under PR #65. This records
delivery evidence for the amendment without changing Section B or the canonical
derivation rules, including rule 9's full SHA-256 preimages/prefixes.

V7-15 Slice 1 completion evidence (2026-10-28): PR #65 merged the approved
three documentation/specification files and six implementation/test files.
Source head `5948562b89bb9fef1823800dc6365578c14e48a4` was squash-merged to
`v7-dev` at `aa89590498bc145e34db5cc77e1f83008df2e9d3`. PR-head required checks
passed 24/24 before merge. Focused tests passed 54 (3 skipped); authority
regression passed 114 (2 skipped); V6 LTS regression passed 99; full pytest
passed 3464 (25 skipped). GPT-6.1 Sol High independent review recorded
P0/P1/P2/OTHER = 0/0/0/0. The source branch was retained. Post-merge CI run
#40650264745 passed 10/10 and CodeQL run #40650264438 passed 3/3. This evidence
completes Slice 1 only; Slices 2 and 3 remain unimplemented and unapproved, and
public routing remains disabled.

For the V7-14-only private registration path, the server-derived
`panel-asset-v7-014-*` ID computed before invocation under canonical rule 9
MUST be registered as the exact `LocalDurableAssetOwner` registry `asset_id`
and returned as `output_asset_id`. The same exact ID must bind the owner row,
PanelAsset, panel attempt record, PanelGenerationEvidence, accepted composition
source manifest, and panel source entries in subsequent composition/output
proofs. A separate randomly issued logical ID
with a hash-only alias lookup is not an acceptable substitute. Storage filenames
remain opaque owner-controlled values independent of the logical asset ID;
no logical ID becomes a filesystem path.

This is a dedicated private V7-14 registration contract, not an optional ID
parameter on the legacy public/provider-neutral registration contract. Only
the server-bound V7-14 adapter may supply the derived ID after verifying the
exact request/reservation, canonical derivation and provider configuration.
Public/client input may not select or override it. Legacy V7-04 registration
continues issuing `asset-generated-*`; its call forms, result contract and
behavior remain unchanged. Reuse the existing owner validation, containment,
staging, atomic placement, registry transaction and verified readback; introduce
no schema, migration, alias table, alternate owner or persistence authority.

An exact replay must verify the same attempt, derived asset ID, provider,
media type, digest and verified registered bytes through the existing owner
contract. It performs no new provider call or replacement registration. A
same-attempt row with another asset ID (including an old `asset-generated-*`
row), an ID bound to another attempt, missing bytes, tamper, or any binding
mismatch fails closed. Do not rename, relabel, repair, overwrite, silently map,
or migrate such existing records. Preserve existing blocked/recovery semantics.
No owner observation or final mode check may ignore an ID mismatch.

This amendment preserves at-most-once provider-start/submit, exact RESERVED
re-preparation, read-only replay, Page fence and revision/CAS boundaries, mode
rechecks, no provider fallback/retry, and existing fail-closed/STOP conditions.
The separately approved Slice 1 implementation is recorded above. The
amendment and its implementation authorize no Slice 2/3 source/test edits or
execution, public API or generic `/generate` change, schema/migration,
dependency/lockfile, I02, live ComfyUI, `main`, release/publication, or further
Git/branch operation. Slices 2 and 3 require their own explicit scope and
approval before implementation.
