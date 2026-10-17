import { describe, expect, it } from "vitest";

import type { PageState } from "@/lib/api/types";
import { canShowApproval, canShowGeneratedAsset } from "@/lib/workflow-view";

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
});
