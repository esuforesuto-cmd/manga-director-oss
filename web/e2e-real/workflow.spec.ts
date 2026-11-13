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

test("confirms explicit storyboard input through the browser proxy and persists it in LocalFile", async ({ page, request }) => {
  const storyboardProjectId = "v7-17-storyboard-confirm-real-e2e";
  const storyboardApiUrl = `${apiOrigin}/projects/${storyboardProjectId}/pages/1`;
  const created = await request.post(`${apiOrigin}/projects`, {
    data: { id: storyboardProjectId, title: "V7-17 explicit storyboard confirmation" }
  });
  expect(created.status(), await created.text()).toBe(201);

  for (const action of ["design", "review"]) {
    const response = await request.post(`${storyboardApiUrl}/${action}`, { data: {} });
    expect(response.status(), await response.text()).toBe(200);
  }
  const reviewed = await request.get(storyboardApiUrl);
  expect(reviewed.status(), await reviewed.text()).toBe(200);
  expect((await reviewed.json()).state).toBe("Reviewed");

  await page.goto(`/projects/${storyboardProjectId}/pages/1`);
  await expect(page.getByRole("heading", { name: "Confirm storyboard input" })).toBeVisible();
  await page.getByLabel("Narrative intent").fill("A courier reaches the sealed gate");
  await page.getByLabel("Character IDs, comma separated").fill("courier, gatekeeper");
  await page.getByLabel("Continuity bindings, one per line").fill("red scarf, visible in every panel\nmap, folded at the corner");
  await page.getByLabel("Action", { exact: true }).fill("The courier raises a hand to knock");
  await page.getByLabel("Background").fill("A stone gate at sunset");
  await page.getByLabel("Composition").fill("Wide view from behind the courier");
  await page.getByLabel("Constraints, one per line").fill("keep the red scarf visible, even when the courier turns\ndo not crop the map, even at the panel edge");
  await page.getByRole("checkbox", { name: "I reviewed these exact panel details and confirm them." }).check();

  const confirmation = page.waitForResponse((response) =>
    response.request().method() === "POST"
    && response.url().endsWith(`/api/projects/${storyboardProjectId}/pages/1/storyboard/confirm`)
  );
  await page.getByRole("button", { name: "Confirm storyboard" }).click();
  const confirmationResponse = await confirmation;
  expect(confirmationResponse.status(), await confirmationResponse.text()).toBe(200);
  await expect(page.getByText("Storyboarded", { exact: true })).toBeVisible();

  const persisted = await request.get(storyboardApiUrl);
  expect(persisted.status(), await persisted.text()).toBe(200);
  const body = await persisted.json();
  expect(body.state).toBe("Storyboarded");
  expect(body.artifacts.storyboard.panels).toEqual([{
    number: 1,
    narrative_intent: "A courier reaches the sealed gate",
    characters: ["courier", "gatekeeper"],
    continuity_bindings: ["red scarf, visible in every panel", "map, folded at the corner"],
    action: "The courier raises a hand to knock",
    background: "A stone gate at sunset",
    composition: "Wide view from behind the courier",
    constraints: ["keep the red scarf visible, even when the courier turns", "do not crop the map, even at the panel edge"]
  }]);
});
