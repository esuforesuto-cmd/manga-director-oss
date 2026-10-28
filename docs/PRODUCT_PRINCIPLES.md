# Product Principles

## Status and precedence

This document is the durable, repository-backed record of long-term product
principles for Manga Director and the future Komaestro brand candidate. It is
not a release plan, implementation specification, legal conclusion, or
authorization to perform external actions.

The current repository and product name remains **Manga Director**. These
principles do not rename the repository, package, imports, commands, public
APIs, or user-facing product without a separate explicit approval.

When a principle in this document has not yet been placed in an approved RFC
or versioned roadmap, treat it as non-binding future direction. The following
remain authoritative for current work:

1. frozen public contracts and compatibility guarantees;
2. `StateMachine`, `WorkflowEngine`, one-Page execution, persisted storyboard,
   completed quality review, and explicit human-approval invariants;
3. the [v6 LTS policy](V6_LTS_POLICY.md) and maintenance plan;
4. accepted RFCs and the current versioned roadmap; and
5. the repository approval gates in `AGENTS.md`.

This document does not authorize I02, a roadmap change, code or dependency
work, a release, publication, trademark filing, account creation, purchase, or
any other external operation. Personal names, addresses, private financial
details, identity documents, and authentication data must never be recorded in
Git or public documentation.

## Free core and creator rights

- Manga Director, and Komaestro if that brand is adopted later, should keep the
  core capabilities required to finish a manga free of product-side paywalls.
- Core manga-completion features and local generation should not be converted
  into paid-only functionality.
- Manga Director charges no additional product-side license fee or commercial-
  use fee merely because a user publishes or sells a work. The repository's
  [MIT License](../LICENSE) remains the authoritative software license.
- External AI services, models, checkpoints, LoRAs, materials, APIs, hosting,
  and other third-party resources remain subject to their providers' prices,
  licenses, usage policies, and availability. Manga Director does not override
  those terms.

## Provider-neutral architecture

- Do not bind the product to one AI vendor, model, or LLM. Preserve replaceable
  Provider boundaries and the existing Factory/Registry direction.
- Manga Director does not need to build its own LLM. Existing or future LLMs
  may be connected through the LLM/Story/Planning Provider boundary.
- ComfyUI is a principal candidate and current reference path for local drawing
  and image generation, not the owner of workflow or approval decisions.
- Provider-specific behavior must not leak into workflow control flow. Preserve
  the contracts established by the
  [provider-neutral image RFC](RFC_V7_002_PROVIDER_NEUTRAL_REAL_IMAGE_DELIVERY.md),
  [ComfyUI local Provider RFC](RFC_V7_003_COMFYUI_LOCAL_PROVIDER.md), and
  [AI Provider backlog](AI_PROVIDERS.md).

## Device and UX priorities

Use the following long-term delivery order unless an approved roadmap says
otherwise:

1. complete the PC core;
2. extend to smartphone, Web, or PWA experiences; and
3. add special optimization for low-specification PCs.

Atelier Mira and ibisPaint are high-priority UX references for approachable
creative workflows. They are references for interaction quality, not authority
to copy protected assets, branding, or implementation, and they do not change
the current roadmap by themselves.

## Resource-efficient generation

Limited free generation quotas, local compute, and user time should not be
wasted. Preserve the established conceptual flow:

~~~text
Planning -> Generation Evidence -> Visual QA -> Human Judgment / Approval
~~~

Any future generation-saving decision layer must sit above that foundation
without bypassing evidence, Visual QA, or explicit human approval. Candidate
decisions include:

- reuse of an existing registered Asset;
- partial repair instead of full regeneration;
- explicit Provider selection;
- prioritization of important panels;
- reuse of approved reference images and Canon evidence; and
- use of generation history to avoid duplicate or known-failing attempts.

These are future decision inputs, not authorization for automatic Provider
switching, automatic retry, silent Asset replacement, or autonomous approval.
Current RFC and roadmap restrictions remain in force until separately changed.
AI may recommend, rank, or prepare evidence, but it must not silently finalize
the human decision. The
[Human-in-the-Loop design](HUMAN_IN_LOOP.md) and current approval contracts
remain authoritative.

## Brand and trademark candidate

- **Komaestro** is retained as the first-choice future trademark and brand
  candidate only. The current Manga Director name must not be changed without
  explicit approval.
- The preferred descriptive candidate is **Komaestro — AI Manga Production
  Studio**.
- Before any formal rename or trademark filing, perform a final search in
  J-PlatPat and other applicable official sources for exact matches and similar
  pronunciations of `Komaestro`, `KOMAESTRO`, and `コマエストロ`, focusing on
  Classes 9 and 42 and expanding the scope when the proposed goods or services
  require it.
- Repository documentation may prepare only non-personal material such as
  prior-mark research, candidate mark forms, standard-character candidates,
  candidate classes, draft goods/services descriptions, expected fees, and a
  checklist of unresolved questions.
- Personal names, addresses, identity data, payment data, and other private
  filing information must not be committed or placed in public documents.

The future operating goal is to automate as much filing preparation as legally
and technically permitted. ChatGPT/Codex may prepare prior-mark research,
classification notes, draft goods/services wording, application drafts, input
checks, and permitted form entry. The applicant retains personal-name and
address entry, identity verification, final confirmation, submission, and
payment. Prefer online, written workflows over telephone or in-person
consultation; consider a qualified professional only when legally necessary or
when an unresolved material risk requires one. This is a future workflow goal,
not authorization to file or operate an external service now.

## Monetization

- Preserve the fully free core principle. Do not place core manga-completion
  features or local generation behind a product paywall.
- Prefer optional, external, or supporting revenue rather than charging for the
  core product. Candidate channels include affiliate links, note/blog content,
  GitHub Sponsors, YouTube, advertising, corporate sponsorship, introductions
  to peripherals or external services, and a future Marketplace.
- Compensation must not distort evaluations, comparison criteria, or
  recommendation order. Clearly disclose advertising, sponsorship, and
  affiliate relationships.
- Keep initial costs low. After Komaestro is complete, use AI where appropriate
  to assist research, article preparation, SEO, site construction, conversion
  paths, and evidence-based analysis and improvement.
- No revenue level or commercial outcome is guaranteed. A future Marketplace
  or other monetization feature still requires its own approved design,
  security and compatibility review, and roadmap placement.

## Adult-content and high-difficulty validation

Do not create a separate "adult Komaestro" application or Core. The shared
Core should reduce manga-production breakage and inconsistency regardless of
genre, while content-specific capabilities remain bounded by Provider terms,
law, distribution rules, and explicit project scope.

Adult-image validation must not block the initial general-audience release.
Use this preferred sequence when it does not conflict with an accepted RFC or
roadmap:

1. complete the general-audience foundation;
2. connect ComfyUI through the approved local boundary;
3. generate an image;
4. perform Visual QA;
5. apply a bounded partial repair;
6. perform Visual QA again;
7. require explicit Human Approval;
8. complete one Page end to end;
9. complete multiple Pages end to end;
10. complete a manga end to end;
11. publish the general-audience product through its separately approved
    release process; and
12. only then add dedicated adult-image validation.

The adult-image work is a local-only, high-difficulty **Private Validation
Suite** on the same Core, not a public fork or separate product. It is limited
to adult characters. Candidate cases include complex physical contact, strong
occlusion, multiple characters, partial repair, post-repair Visual QA, and
character consistency.

Adult images, real prompts, filenames, metadata, and equivalent sensitive test
artifacts must not be sent to GitHub, public CI, OpenAI/Codex, or another cloud
service. Keep them outside the repository and public documentation in a local-
only environment. Until this dedicated validation is complete, public claims
must not state or imply that Manga Director/Komaestro prevents failures in
adult-content generation.

## LLM and ComfyUI development order

- Preserve the replaceable LLM/Story Provider seam; a first-party LLM is not a
  prerequisite.
- Full adult-oriented LLM support is not an initial-release requirement.
- After the general-audience Core is ready, prioritize approved ComfyUI
  connectivity and real-image end-to-end completion so the product reaches a
  complete-manga workflow sooner. Add deeper LLM integration later when the
  workflow requires it.
- This is a sequencing principle, not a claim about current completion and not
  permission to reorder an accepted roadmap. If it conflicts with a frozen
  design or approved roadmap, record it as future, non-binding direction and
  stop before changing scope.

## Codex model operating policy

- When the specified model is available in the current Codex environment, use
  **GPT-6 Luna High** as the default mainline execution model. It handles
  routine, lightweight work and authorized investigation, planning,
  implementation, documentation, and validation that do not meet the
  GPT-6 Astra escalation conditions below.
- Before an important result involving frozen specifications, public APIs,
  compatibility, architecture, complex implementation, P0/P1 work, or
  security work is treated as complete or advances to the next write stage,
  require an independent read-only review by **GPT-6.1 Sol High** in a
  separate agent or context. The independent reviewer must not modify files.
- Use **GPT-5.6 Sol High** only for an additional independent read-only review
  when an unresolved disagreement that could change the conclusion remains
  about correctness, severity, compatibility, security, required validation,
  or an approval boundary.
- Use **GPT-6 Astra** only for a critical, high-difficulty P0/P1, security,
  frozen-contract, public-API, compatibility, or architecture issue that
  remains unresolved after the preceding review stages. Record the escalation
  reason and actual reasoning setting. Astra does not gain approval or
  publication authority.
- After an important stage is complete, return to **GPT-6 Luna High** for the
  next routine stage, when it is available in the current Codex environment.
- When practical, use different models for implementation and final review.
- State the intended model explicitly in Codex prompts so the execution and
  review roles are auditable.
- If a specified model is unavailable in the current Codex environment, stop
  before starting the stage that requires it, report the unavailability, and
  require explicit approval before using a substitute.
- Model selection does not relax file allowlists, approval gates, the
  AUTO-PROGRESS and explicit-approval boundaries in `AGENTS.md`, validation,
  privacy restrictions, v6 LTS scope, or release controls.

Model availability may change. Never claim a substitute was the specified
model, and preserve the role separation and review rigor above.
