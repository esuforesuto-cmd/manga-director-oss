"use client";

import { useState, type FormEvent } from "react";

import { api } from "@/lib/api/client";
import type {
  HumanVisualCriterion,
  HumanVisualOutcome,
  OverallHumanJudgment,
  VisualReviewEvidenceResponse,
  VisualReviewReadinessResponse
} from "@/lib/api/types";

import styles from "./page-workflow.module.css";

const visualCriteria: HumanVisualCriterion[] = [
  "character_identity", "face", "costume", "props", "pose", "gaze",
  "emotion", "screen_direction", "location", "time", "composition",
  "panel_intent", "visible_corruption", "truncation", "watermark",
  "unsafe_content", "unintended_text", "continuity_comparison"
];

type VisualDecision = { outcome: HumanVisualOutcome | ""; rationale: string };

function emptyVisualDecisions(): Record<HumanVisualCriterion, VisualDecision> {
  return Object.fromEntries(
    visualCriteria.map((criterion) => [criterion, { outcome: "", rationale: "" }])
  ) as Record<HumanVisualCriterion, VisualDecision>;
}

export function HumanVisualReviewForm({
  projectId,
  pageNumber
}: Readonly<{ projectId: string; pageNumber: number }>) {
  const [reviewerId, setReviewerId] = useState("");
  const [reviewedAt, setReviewedAt] = useState("");
  const [decisions, setDecisions] = useState(emptyVisualDecisions);
  const [overallJudgment, setOverallJudgment] = useState<OverallHumanJudgment | "">("");
  const [rationale, setRationale] = useState("");
  const [result, setResult] = useState<
    VisualReviewReadinessResponse | VisualReviewEvidenceResponse | null
  >(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    const recordingEvidence = submitter?.value === "record-evidence";
    setResult(null);
    setError("");
    const parsedTimestamp = new Date(reviewedAt);
    if (!overallJudgment || Number.isNaN(parsedTimestamp.valueOf())) {
      setError("Complete the explicit review timestamp and overall judgment.");
      return;
    }
    setSubmitting(true);
    try {
      const body = {
        reviewerId,
        reviewedAt: parsedTimestamp.toISOString(),
        checklist: visualCriteria.map((criterion) => ({
          criterion,
          outcome: decisions[criterion].outcome as HumanVisualOutcome,
          rationale: decisions[criterion].rationale
        })),
        overallJudgment,
        rationale
      };
      const response = recordingEvidence
        ? await api.pages.recordVisualReviewEvidence(projectId, pageNumber, body)
        : await api.pages.assessVisualReview(projectId, pageNumber, body);
      setResult(response);
    } catch {
      setError(recordingEvidence
        ? "The durable visual review evidence operation is unavailable."
        : "The advisory visual assessment is unavailable.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className={styles.panel} aria-labelledby="visual-review-heading">
      <h2 id="visual-review-heading">Human visual review readiness</h2>
      <p>Assess readiness is transient. Recording creates historical evidence only and never approves the page.</p>
      <form onSubmit={submit}>
        <label>
          Reviewer reference
          <input required maxLength={200} value={reviewerId} onChange={(event) => setReviewerId(event.target.value)} />
        </label>
        <label>
          Reviewed at
          <input required type="datetime-local" value={reviewedAt} onChange={(event) => setReviewedAt(event.target.value)} />
        </label>
        {visualCriteria.map((criterion) => (
          <fieldset key={criterion}>
            <legend>{criterion.replaceAll("_", " ")}</legend>
            <label>
              Outcome
              <select
                required
                value={decisions[criterion].outcome}
                onChange={(event) => setDecisions((current) => ({
                  ...current,
                  [criterion]: { ...current[criterion], outcome: event.target.value as HumanVisualOutcome }
                }))}
              >
                <option value="">Select explicitly</option>
                <option value="acceptable">Acceptable</option>
                <option value="needs_review">Needs review</option>
                <option value="blocked">Blocked</option>
                {criterion === "props" || criterion === "continuity_comparison" ? (
                  <option value="not_applicable">Not applicable</option>
                ) : null}
              </select>
            </label>
            <label>
              Rationale
              <input
                required
                maxLength={500}
                value={decisions[criterion].rationale}
                onChange={(event) => setDecisions((current) => ({
                  ...current,
                  [criterion]: { ...current[criterion], rationale: event.target.value }
                }))}
              />
            </label>
          </fieldset>
        ))}
        <label>
          Overall judgment
          <select required value={overallJudgment} onChange={(event) => setOverallJudgment(event.target.value as OverallHumanJudgment)}>
            <option value="">Select explicitly</option>
            <option value="acceptable_for_approval_consideration">Acceptable for approval consideration</option>
            <option value="further_review_required">Further review required</option>
            <option value="blocked">Blocked</option>
          </select>
        </label>
        <label>
          Overall rationale
          <input required maxLength={500} value={rationale} onChange={(event) => setRationale(event.target.value)} />
        </label>
        <button type="submit" name="reviewAction" value="assess" disabled={submitting}>
          {submitting ? "Working…" : "Assess readiness"}
        </button>
        <button type="submit" name="reviewAction" value="record-evidence" disabled={submitting}>
          {submitting ? "Working…" : "Record review evidence"}
        </button>
      </form>
      {error ? <p className="inlineError" role="alert">{error}</p> : null}
      {result ? (
        <div aria-live="polite">
          <p>Advisory result: {result.status}</p>
          {"evidenceRecorded" in result ? (
            <p>
              Historical evidence recorded
              {result.idempotentReplay ? " (existing identical record confirmed)" : ""}.
            </p>
          ) : null}
          <ul>{result.findings.map((finding) => <li key={`${finding.code}:${finding.criterion}`}>{finding.code}</li>)}</ul>
        </div>
      ) : null}
    </section>
  );
}
