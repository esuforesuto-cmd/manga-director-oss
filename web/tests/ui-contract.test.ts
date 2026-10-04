import { describe, expect, it } from "vitest";

import type { PageState } from "@/lib/api/types";
import { canShowApproval } from "@/lib/workflow-view";

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
});
