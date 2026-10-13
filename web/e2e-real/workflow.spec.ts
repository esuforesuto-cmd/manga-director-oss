import { expect, test } from "@playwright/test";

const projectId = "v7-02-real-e2e";
const apiOrigin = "http://127.0.0.1:8000";
const apiUrl = `${apiOrigin}/projects/${projectId}/pages/1`;

test("runs one persisted page through the real local delivery boundary", async ({ page, request }) => {
  const created = await request.post(`${apiOrigin}/projects`, {
    data: { id: projectId, title: "V7-02 real delivery" }
  });
  expect(created.status(), await created.text()).toBe(201);

  await page.goto(`/projects/${projectId}/pages/1`);
  await expect(page.getByRole("heading", { name: "Page 1" })).toBeVisible();
  await page.waitForLoadState("networkidle");

  for (const action of [
    "Design",
    "Review",
    "Storyboard",
    "Build prompt",
    "Generate",
    "Quality check"
  ]) {
    const apiAction = { "Build prompt": "prompt", "Quality check": "quality" }[action]
      ?? action.toLowerCase();
    const responsePromise = page.waitForResponse((response) =>
      response.request().method() === "POST"
      && response.url().endsWith(`/projects/${projectId}/pages/1/${apiAction}`)
    );
    await page.getByRole("button", { name: action, exact: true }).click();
    expect((await responsePromise).status()).toBe(200);
  }

  await expect(page.getByRole("heading", { name: "Human approval" })).toBeVisible();
  const qualityChecked = await request.get(apiUrl);
  expect(qualityChecked.status()).toBe(200);
  expect((await qualityChecked.json()).state).toBe("QualityChecked");

  await page.getByLabel("Approved by").fill("v7-02-e2e-reviewer");
  const approvalResponsePromise = page.waitForResponse((response) =>
    response.request().method() === "POST" && response.url().endsWith(`${apiUrl}/approve`)
  );
  await page.getByRole("button", { name: "Approve page" }).click();
  expect((await approvalResponsePromise).status()).toBe(200);
  await expect(page.getByText("Approved", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Human approval" })).toHaveCount(0);

  await page.reload();
  await expect(page.getByText("Approved", { exact: true })).toBeVisible();

  const persisted = await request.get(apiUrl);
  expect(persisted.status()).toBe(200);
  const body = await persisted.json();
  expect(body.state).toBe("Approved");
  expect(body.artifacts.storyboard).toBeTruthy();
  expect(body.artifacts.approval.approved_by).toBe("v7-02-e2e-reviewer");
});
