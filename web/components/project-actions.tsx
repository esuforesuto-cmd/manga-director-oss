"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { ApiClientError, api } from "@/lib/api/client";

export function ProjectActions({ projectId }: Readonly<{ projectId: string }>) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function execute(kind: "run" | "resume") {
    setError(null);
    startTransition(async () => {
      try {
        await api.projects[kind](projectId);
        router.refresh();
      } catch (cause) {
        setError(cause instanceof ApiClientError ? cause.message : "Workflow request failed.");
      }
    });
  }

  return (
    <div aria-live="polite">
      <div className="actionGroup">
        <button className="button" type="button" disabled={pending} onClick={() => execute("run")}>Run project</button>
        <button className="button secondary" type="button" disabled={pending} onClick={() => execute("resume")}>Resume project</button>
      </div>
      {error ? <p className="inlineError" role="alert">{error}</p> : null}
    </div>
  );
}
