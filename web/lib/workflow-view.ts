import type { PageAction, PageDetail, StoryboardPanelSummary } from "@/lib/api/types";

/** UI-only guards; a compatible HTTP application remains the transition authority. */
export function canShowApproval(page: Pick<PageDetail, "approvalRequired" | "state">): boolean {
  return page.state === "QualityChecked" && page.approvalRequired;
}

/** Only a fully persisted, contiguous Storyboard can authorize a panel form. */
export function persistedStoryboardPanels(page: Pick<PageDetail, "artifacts">): StoryboardPanelSummary[] | null {
  const storyboard = page.artifacts.storyboard;
  if (!storyboard || typeof storyboard !== "object" || Array.isArray(storyboard)) return null;
  const panels = (storyboard as Record<string, unknown>).panels;
  if (!Array.isArray(panels) || panels.length < 1 || panels.length > 16) return null;
  const valid = panels.every((value, index) => {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    const panel = value as Record<string, unknown>;
    return panel.number === index + 1
      && ["narrative_intent", "action", "background", "composition"].every((key) => typeof panel[key] === "string" && (panel[key] as string).trim().length > 0)
      && ["characters", "continuity_bindings", "constraints"].every((key) => Array.isArray(panel[key]) && (panel[key] as unknown[]).length > 0 && (panel[key] as unknown[]).every((item) => typeof item === "string" && item.trim().length > 0));
  });
  return valid ? panels as StoryboardPanelSummary[] : null;
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

/** Download remains an explicit action for one exact, already Approved image. */
export function canShowApprovedAssetDownload(
  page: Pick<PageDetail, "artifacts" | "state">
): boolean {
  return page.state === "Approved" && canShowGeneratedAsset(page);
}

/** Human readiness is advisory and never reopens an Approved Page. */
export function canShowVisualReview(
  page: Pick<PageDetail, "artifacts" | "state">
): boolean {
  return ["Generated", "QualityChecked"].includes(page.state) && canShowGeneratedAsset(page);
}

/** History is an explicit read-only action and remains available after approval. */
export function canShowVisualReviewEvidenceHistory(
  page: Pick<PageDetail, "state">
): boolean {
  return ["Generated", "QualityChecked", "Approved"].includes(page.state);
}
