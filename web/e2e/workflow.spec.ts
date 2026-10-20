import { expect, test } from "@playwright/test";

test("shows human approval only for a QualityChecked page", async ({ page, request }) => {
  async function reviewEvidenceCount(): Promise<number> {
    const response = await request.get("http://127.0.0.1:4010/test-only/review-evidence-count");
    expect(response.status()).toBe(200);
    return (await response.json()).count;
  }

  async function reviewEvidenceHistoryReadCount(): Promise<number> {
    const response = await request.get(
      "http://127.0.0.1:4010/test-only/review-evidence-history-read-count"
    );
    expect(response.status()).toBe(200);
    return (await response.json()).count;
  }

  const created = await request.post("http://127.0.0.1:4010/projects", { data: { id: "demo", title: "Demo manga" } });
  expect(created.status()).toBe(201);

  for (const action of ["Design", "Review", "Storyboard", "Build prompt", "Generate", "Quality check"]) {
    const apiAction = { "Build prompt": "prompt", "Quality check": "quality" }[action] ?? action.toLowerCase();
    const response = await request.post(`http://127.0.0.1:4010/projects/demo/pages/1/${apiAction}`);
    expect(response.status()).toBe(200);
  }

  await page.goto("/projects/demo/pages/1");
  const generated = page.getByRole("img", { name: "Generated asset for page 1" });
  await expect(generated).toBeVisible();
  await expect(generated).toHaveAttribute(
    "src",
    "http://127.0.0.1:4010/projects/demo/pages/1/generated-asset"
  );
  await expect(page.getByRole("heading", { name: "Human approval" })).toBeVisible();
  expect(await reviewEvidenceCount()).toBe(0);
  expect(await reviewEvidenceHistoryReadCount()).toBe(0);
  const history = page.getByRole("region", { name: "Human visual review evidence history" });
  await expect(history).toBeVisible();
  await history.getByRole("button", { name: "Show review evidence history" }).click();
  await expect(history.getByText("No review evidence has been recorded.")).toBeVisible();
  expect(await reviewEvidenceHistoryReadCount()).toBe(1);
  const review = page.getByRole("region", { name: "Human visual review readiness" });
  await expect(review).toBeVisible();
  await review.getByLabel("Reviewer reference").fill("reviewer:local");
  await review.getByLabel("Reviewed at").fill("2026-10-18T12:00");
  for (const fieldset of await review.locator("fieldset").all()) {
    await fieldset.locator("select").selectOption("acceptable");
    await fieldset.locator("input").fill("Reviewed directly");
  }
  await review.getByLabel("Overall judgment").selectOption("acceptable_for_approval_consideration");
  await review.getByLabel("Overall rationale").fill("Complete local visual review");
  await review.getByRole("button", { name: "Assess readiness" }).click();
  await expect(review.getByText("Advisory result: ready")).toBeVisible();
  await expect(review.getByText(/Historical evidence recorded/)).toHaveCount(0);
  expect(await reviewEvidenceCount()).toBe(0);
  await review.getByRole("button", { name: "Record review evidence" }).click();
  await expect(review.getByText("Historical evidence recorded.")).toBeVisible();
  expect(await reviewEvidenceCount()).toBe(1);
  await history.getByRole("button", { name: "Show review evidence history" }).click();
  await expect(history.getByRole("article", { name: "Review evidence review:demo:001" })).toBeVisible();
  await expect(history.getByText("Advisory status: ready")).toBeVisible();
  await expect(history.getByText("Ready indicator: true — not approval")).toBeVisible();
  expect(await reviewEvidenceHistoryReadCount()).toBe(2);
  await review.getByRole("button", { name: "Record review evidence" }).click();
  await expect(
    review.getByText("Historical evidence recorded (existing identical record confirmed).")
  ).toBeVisible();
  expect(await reviewEvidenceCount()).toBe(1);
  await expect(page.getByLabel("Approved by")).toHaveValue("");

  await page.reload();
  await expect(page.getByText("Advisory result: ready")).toHaveCount(0);
  await expect(page.getByText(/Historical evidence recorded/)).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Human approval" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Download approved PNG" })).toHaveCount(0);
  expect(await reviewEvidenceCount()).toBe(1);
  expect(await reviewEvidenceHistoryReadCount()).toBe(2);

  await page.getByLabel("Approved by").fill("editor:local");
  await page.getByRole("button", { name: "Approve page" }).click();
  const downloadLink = page.getByRole("link", { name: "Download approved PNG" });
  await expect(downloadLink).toBeVisible();
  await expect(downloadLink).toHaveAttribute(
    "href",
    "http://127.0.0.1:4010/projects/demo/pages/1/approved-asset-download"
  );
  const approvedHistory = page.getByRole("region", { name: "Human visual review evidence history" });
  await expect(approvedHistory).toBeVisible();
  await approvedHistory.getByRole("button", { name: "Show review evidence history" }).click();
  await expect(approvedHistory.getByText("Advisory status: ready")).toBeVisible();
  await expect(page.getByLabel("Approved by")).toHaveCount(0);
  expect(await reviewEvidenceHistoryReadCount()).toBe(3);
  const downloadPromise = page.waitForEvent("download");
  await downloadLink.click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("page-1.png");
  expect(await reviewEvidenceCount()).toBe(1);
});
