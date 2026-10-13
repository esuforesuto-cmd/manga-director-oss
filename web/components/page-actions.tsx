"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { ApiClientError, api } from "@/lib/api/client";
import type { PageAction } from "@/lib/api/types";

const labels: Record<PageAction, string> = {
  design: "Design", review: "Review", storyboard: "Storyboard", dialogue: "Dialogue",
  prompt: "Build prompt", generate: "Generate", quality: "Quality check", continuity: "Continuity check",
  approve: "Approve"
};

export function PageActions({
  projectId,
  pageNumber,
  actions
}: Readonly<{ projectId: string; pageNumber: number; actions: PageAction[] }>) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function execute(action: PageAction) {
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
