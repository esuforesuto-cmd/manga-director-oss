"use client";

import { FormEvent, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { ApiClientError, api } from "@/lib/api/client";

export function ApprovalForm({ projectId, pageNumber }: Readonly<{ projectId: string; pageNumber: number }>) {
  const router = useRouter();
  const [approvedBy, setApprovedBy] = useState("");
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    startTransition(async () => {
      try {
        await api.workflow.execute(projectId, pageNumber, "approve", { approved_by: approvedBy });
        router.refresh();
      } catch (cause) {
        setError(cause instanceof ApiClientError ? cause.message : "Approval failed.");
      }
    });
  }

  return <form className="approvalPanel" onSubmit={submit}><h2>Human approval</h2><p>Quality review is complete. Record the responsible approver.</p><label htmlFor="approved-by">Approved by</label><input id="approved-by" required value={approvedBy} onChange={(event) => setApprovedBy(event.target.value)} /><button className="button" disabled={pending} type="submit">Approve page</button>{error ? <p className="inlineError" role="alert">{error}</p> : null}</form>;
}
