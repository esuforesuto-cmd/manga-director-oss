import type { PageAction, PageDetail } from "@/lib/api/types";

/** UI-only guards; a compatible HTTP application remains the transition authority. */
export function canShowApproval(page: Pick<PageDetail, "approvalRequired" | "state">): boolean {
  return page.state === "QualityChecked" && page.approvalRequired;
}

/** The server supplies legal actions, so the UI never derives transitions. */
export function availableWorkflowActions(page: Pick<PageDetail, "workflow">): PageAction[] {
  return page.workflow.availableActions.filter(
    (action): action is PageAction => action !== "run" && action !== "resume" && action !== "approve"
  );
}
