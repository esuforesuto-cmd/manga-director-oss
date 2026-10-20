import { describe, expect, it } from "vitest";

import type { PageState } from "@/lib/api/types";
import {
  canShowApproval,
  canShowApprovedAssetDownload,
  canShowGeneratedAsset,
  canShowVisualReview,
  canShowVisualReviewEvidenceHistory
} from "@/lib/workflow-view";

describe("UI workflow contract", () => {
  it("exposes approval only through the API-provided approval flag", () => {
    const page = {
      approvalRequired: true,
      state: "QualityChecked" as PageState
    };

    expect(canShowApproval(page)).toBe(true);
  });

  it("does not expose approval in an invalid state even if a malformed response sets the flag", () => {
    expect(
      canShowApproval({ approvalRequired: true, state: "Draft" as PageState })
    ).toBe(false);
  });

  it.each(["Generated", "QualityChecked", "Approved"] as PageState[])(
    "shows the fixed generated-asset route only for an exact logical artifact in %s",
    (state) => {
      expect(canShowGeneratedAsset({
        state,
        artifacts: {
          image: { artifact_kind: "logical_output_asset", output_asset_id: "asset:001" }
        }
      })).toBe(true);
    }
  );

  it("rejects path-shaped, extra-field, and pre-generated image artifacts", () => {
    expect(canShowGeneratedAsset({
      state: "Generated" as PageState,
      artifacts: { image: { path: "C:/private/image.png" } }
    })).toBe(false);
    expect(canShowGeneratedAsset({
      state: "Generated" as PageState,
      artifacts: {
        image: {
          artifact_kind: "logical_output_asset",
          output_asset_id: "asset:001",
          url: "http://provider.invalid/image.png"
        }
      }
    })).toBe(false);
    expect(canShowGeneratedAsset({
      state: "PromptBuilt" as PageState,
      artifacts: {
        image: { artifact_kind: "logical_output_asset", output_asset_id: "asset:001" }
      }
    })).toBe(false);
  });

  it.each(["Generated", "QualityChecked"] as PageState[])(
    "shows transient visual review only for an assessable exact artifact in %s",
    (state) => {
      expect(canShowVisualReview({
        state,
        artifacts: {
          image: { artifact_kind: "logical_output_asset", output_asset_id: "asset:001" }
        }
      })).toBe(true);
    }
  );

  it.each(["PromptBuilt", "Approved"] as PageState[])(
    "does not open the visual review boundary in %s",
    (state) => {
      expect(canShowVisualReview({
        state,
        artifacts: {
          image: { artifact_kind: "logical_output_asset", output_asset_id: "asset:001" }
        }
      })).toBe(false);
    }
  );

  it("keeps explicit review evidence separate from approval authority", () => {
    const artifact = {
      image: { artifact_kind: "logical_output_asset", output_asset_id: "asset:001" }
    };
    expect(canShowVisualReview({
      state: "Generated" as PageState,
      artifacts: artifact
    })).toBe(true);
    expect(canShowApproval({
      state: "Generated" as PageState,
      approvalRequired: false
    })).toBe(false);
    expect(canShowVisualReview({
      state: "QualityChecked" as PageState,
      artifacts: artifact
    })).toBe(true);
    expect(canShowApproval({
      state: "QualityChecked" as PageState,
      approvalRequired: true
    })).toBe(true);
  });

  it.each(["Generated", "QualityChecked", "Approved"] as PageState[])(
    "shows read-only evidence history without deriving approval in %s",
    (state) => {
      expect(canShowVisualReviewEvidenceHistory({ state })).toBe(true);
    }
  );

  it.each(["Draft", "Designed", "Reviewed", "Storyboarded", "PromptBuilt"] as PageState[])(
    "does not expose evidence history before generation in %s",
    (state) => {
      expect(canShowVisualReviewEvidenceHistory({ state })).toBe(false);
    }
  );

  it("shows approved download only for the exact Approved logical artifact", () => {
    const artifact = {
      image: { artifact_kind: "logical_output_asset", output_asset_id: "asset:001" }
    };
    expect(canShowApprovedAssetDownload({
      state: "Approved" as PageState,
      artifacts: artifact
    })).toBe(true);
    expect(canShowApprovedAssetDownload({
      state: "QualityChecked" as PageState,
      artifacts: artifact
    })).toBe(false);
    expect(canShowApprovedAssetDownload({
      state: "Approved" as PageState,
      artifacts: { image: { path: "C:/private/image.png" } }
    })).toBe(false);
  });
});
