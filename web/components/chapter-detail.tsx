"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import type { ChapterDetail } from "@/lib/api/types";
import { ApiClientError, api } from "@/lib/api/client";

import styles from "./chapter-detail.module.css";

export function ChapterDetailView({
  projectId,
  chapter
}: Readonly<{ projectId: string; chapter: ChapterDetail }>) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function runChapter() {
    setError(null);
    startTransition(async () => {
      try {
        await api.chapters.run(projectId, chapter.id);
        router.refresh();
      } catch (cause) {
        setError(cause instanceof ApiClientError ? cause.message : "Chapter request failed.");
      }
    });
  }

  return (
    <section aria-labelledby="chapter-heading">
      <div className="pageHeading">
        <div><p className="eyebrow">{projectId}</p><h1 id="chapter-heading">{chapter.title}</h1></div>
        <button className="button" type="button" disabled={pending} onClick={runChapter}>Run chapter</button>
      </div>
      {error ? <p className="inlineError" role="alert">{error}</p> : null}
      <div className={styles.tableWrap}>
        <table>
          <caption>Pages</caption>
          <thead><tr><th>Page</th><th>State</th><th>Quality</th><th>Approval</th><th><span className="srOnly">Open</span></th></tr></thead>
          <tbody>
            {chapter.pages.map((page) => (
              <tr key={page.pageNumber}>
                <td>{page.pageNumber}</td><td>{page.state}</td><td>{page.qualityPassed === null ? "—" : page.qualityPassed ? "Passed" : "Failed"}</td><td>{page.approved ? "Approved" : "Pending"}</td>
                <td><a href={`/projects/${encodeURIComponent(projectId)}/pages/${page.pageNumber}`}>Open page</a></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
