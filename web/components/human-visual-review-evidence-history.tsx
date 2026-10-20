"use client";

import { useState } from "react";

import { api } from "@/lib/api/client";
import type { VisualReviewEvidenceHistoryResponse } from "@/lib/api/types";

import styles from "./page-workflow.module.css";

export function HumanVisualReviewEvidenceHistory({
  projectId,
  pageNumber
}: Readonly<{ projectId: string; pageNumber: number }>) {
  const [history, setHistory] = useState<VisualReviewEvidenceHistoryResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function showHistory() {
    setHistory(null);
    setError("");
    setLoading(true);
    try {
      setHistory(await api.pages.getVisualReviewEvidenceHistory(projectId, pageNumber));
    } catch {
      setError("The read-only visual review evidence history is unavailable.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className={styles.panel} aria-labelledby="visual-review-history-heading">
      <h2 id="visual-review-history-heading">Human visual review evidence history</h2>
      <p>
        Every result is historical advisory evidence only. It is not approval or a workflow
        instruction.
      </p>
      <button type="button" onClick={showHistory} disabled={loading}>
        {loading ? "Loading…" : "Show review evidence history"}
      </button>
      {error ? <p className="inlineError" role="alert">{error}</p> : null}
      {history ? (
        <div aria-live="polite">
          <p>Complete read-only history: {history.recordCount} record(s).</p>
          {history.records.length === 0 ? <p>No review evidence has been recorded.</p> : null}
          {history.records.map((record) => (
            <article key={record.reviewId} aria-label={`Review evidence ${record.reviewId}`}>
              <h3>{record.reviewId}</h3>
              <p>Advisory status: {record.status}</p>
              <p>Ready indicator: {record.ready ? "true" : "false"} — not approval</p>
              <dl>
                <dt>Output asset</dt><dd>{record.outputAssetId}</dd>
                <dt>Reviewer reference</dt><dd>{record.reviewerId}</dd>
                <dt>Reviewed at</dt><dd>{record.reviewedAt}</dd>
                <dt>Recorded Page state</dt><dd>{record.pageState}</dd>
                <dt>Overall judgment</dt><dd>{record.overallJudgment}</dd>
                <dt>Overall rationale</dt><dd>{record.rationale}</dd>
              </dl>
              <details>
                <summary>Complete checklist</summary>
                <ul>
                  {record.checklist.map((item) => (
                    <li key={item.criterion}>
                      {item.criterion}: {item.outcome} — {item.rationale}
                    </li>
                  ))}
                </ul>
              </details>
              <h4>Findings</h4>
              {record.findings.length ? (
                <ul>
                  {record.findings.map((finding) => (
                    <li key={`${finding.code}:${finding.criterion}`}>
                      {finding.code}: {finding.message}
                      {finding.criterion ? ` (${finding.criterion})` : ""}
                    </li>
                  ))}
                </ul>
              ) : <p>None.</p>}
              <h4>Missing prerequisites</h4>
              {record.missingPrerequisites.length ? (
                <ul>
                  {record.missingPrerequisites.map((item) => <li key={item}>{item}</li>)}
                </ul>
              ) : <p>None.</p>}
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
