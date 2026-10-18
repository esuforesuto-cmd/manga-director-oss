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

/** Image display is derived only from the selected Page and its exact logical descriptor. */
export function canShowGeneratedAsset(
  page: Pick<PageDetail, "artifacts" | "state">
): boolean {
  if (!["Generated", "QualityChecked", "Approved"].includes(page.state)) {
    return false;
  }
  const image = page.artifacts.image;
  return Boolean(
    image
    && typeof image === "object"
    && !Array.isArray(image)
    && Object.keys(image).sort().join(",") === "artifact_kind,output_asset_id"
    && (image as Record<string, unknown>).artifact_kind === "logical_output_asset"
    && typeof (image as Record<string, unknown>).output_asset_id === "string"
  );
}

/** Human readiness is advisory and never reopens an Approved Page. */
export function canShowVisualReview(
  page: Pick<PageDetail, "artifacts" | "state">
): boolean {
  return ["Generated", "QualityChecked"].includes(page.state) && canShowGeneratedAsset(page);
}
