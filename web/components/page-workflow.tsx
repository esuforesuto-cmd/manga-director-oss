import type { PageDetail } from "@/lib/api/types";

import { api } from "@/lib/api/client";
import { ApprovalForm } from "./approval-form";
import { PageActions } from "./page-actions";
import styles from "./page-workflow.module.css";
import { availableWorkflowActions, canShowApproval, canShowGeneratedAsset } from "@/lib/workflow-view";

const stages = ["Page Design", "Review", "Storyboard", "Dialogue", "Prompt", "Generated Image", "Quality", "Continuity", "Approval"];

export function PageWorkflowView({
  projectId,
  page
}: Readonly<{ projectId: string; page: PageDetail }>) {
  return (
    <section aria-labelledby="page-heading">
      <div className="pageHeading">
        <div><p className="eyebrow">{projectId}</p><h1 id="page-heading">Page {page.pageNumber}</h1></div>
        <span className={styles.state}>{page.state}</span>
      </div>
      <ol className={styles.stages}>{stages.map((stage) => <li key={stage}>{stage}</li>)}</ol>
      <section className={styles.panel} aria-labelledby="actions-heading">
        <h2 id="actions-heading">Workflow actions</h2>
        <PageActions projectId={projectId} pageNumber={page.pageNumber} actions={availableWorkflowActions(page)} />
      </section>
      {canShowGeneratedAsset(page) ? (
        <section className={styles.panel} aria-labelledby="generated-asset-heading">
          <h2 id="generated-asset-heading">Generated image</h2>
          {/* The local API performs the authoritative Page-to-bytes validation. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            alt={`Generated asset for page ${page.pageNumber}`}
            src={api.pages.generatedAssetUrl(projectId, page.pageNumber)}
          />
        </section>
      ) : null}
      {canShowApproval(page) ? <ApprovalForm projectId={projectId} pageNumber={page.pageNumber} /> : null}
      <section className={styles.panel} aria-labelledby="input-heading">
        <h2 id="input-heading">Input</h2>
        <pre>{JSON.stringify(page.input ?? {}, null, 2)}</pre>
      </section>
      <section className={styles.panel} aria-labelledby="artifacts-heading">
        <h2 id="artifacts-heading">Artifacts</h2>
        <pre>{JSON.stringify(page.artifacts, null, 2)}</pre>
      </section>
      <section className={styles.panel} aria-labelledby="messages-heading">
        <h2 id="messages-heading">Messages and errors</h2>
        <ul>{page.messages.map((message) => <li key={message}>{message}</li>)}</ul>
        {page.errors.length ? <ul className="inlineError">{page.errors.map((error) => <li key={error.code}>{error.message}</li>)}</ul> : null}
        <p>Execution time: {page.executionTimeMs === null ? "—" : `${page.executionTimeMs} ms`}</p>
      </section>
    </section>
  );
}
