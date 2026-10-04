"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { ApiClientError, api } from "@/lib/api/client";
import type { WorkflowAction } from "@/lib/api/types";

const labels: Record<WorkflowAction, string> = {
  design: "Design", review: "Review", storyboard: "Storyboard", dialogue: "Dialogue",
  prompt: "Build prompt", generate: "Generate", quality: "Quality check", continuity: "Continuity check",
  approve: "Approve", run: "Run", resume: "Resume", retry: "Retry failed step"
};

export function PageActions({
  projectId,
  pageNumber,
  actions
}: Readonly<{ projectId: string; pageNumber: number; actions: WorkflowAction[] }>) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function execute(action: WorkflowAction) {
    setError(null);
    startTransition(async () => {
      try {
        await api.workflow.execute(projectId, pageNumber, action);
        router.refresh();
      } catch (cause) {
        setError(cause instanceof ApiClientError ? cause.message : "Page action failed.");
      }
    });
  }

  return <div aria-live="polite"><div className="actionGroup">{actions.map((action) => <button className="button secondary" type="button" disabled={pending} key={action} onClick={() => execute(action)}>{labels[action]}</button>)}</div>{error ? <p className="inlineError" role="alert">{error}</p> : null}</div>;
}
