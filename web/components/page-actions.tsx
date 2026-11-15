"use client";

import { useId, useState, useTransition } from "react";
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
  const storyboardHelpId = useId();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const hasStoryboard = actions.includes("storyboard");

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

  return (
    <div aria-live="polite">
      <div className="actionGroup">
        {actions.map((action) => (
          <button
            aria-describedby={action === "storyboard" ? storyboardHelpId : undefined}
            className="button secondary"
            disabled={pending}
            key={action}
            onClick={() => execute(action)}
            type="button"
          >
            {labels[action]}
          </button>
        ))}
      </div>
      {hasStoryboard ? (
        <p id={storyboardHelpId}>Creates panels from the page design using default details.</p>
      ) : null}
      {error ? <p className="inlineError" role="alert">{error}</p> : null}
    </div>
  );
}
