import { expect, test, type Page, type APIRequestContext } from "@playwright/test";

const apiOrigin = "http://127.0.0.1:8000";

async function createReviewedPage(request: APIRequestContext, projectId: string): Promise<string> {
  const pageUrl = `${apiOrigin}/projects/${projectId}/pages/1`;
  const created = await request.post(`${apiOrigin}/projects`, {
    data: { id: projectId, title: "V7-17 explicit storyboard confirmation" }
  });
  expect(created.status(), await created.text()).toBe(201);

  for (const action of ["design", "review"]) {
    const response = await request.post(`${pageUrl}/${action}`, { data: {} });
    expect(response.status(), await response.text()).toBe(200);
  }

  const reviewed = await request.get(pageUrl);
  expect(reviewed.status(), await reviewed.text()).toBe(200);
  expect((await reviewed.json()).state).toBe("Reviewed");
  return pageUrl;
}

async function fillAndConfirm(page: Page): Promise<void> {
  await page.getByLabel("Narrative intent").fill("A courier reaches the sealed gate");
  await page.getByLabel("Character IDs, comma separated").fill("courier, gatekeeper");
  await page.getByLabel("Continuity bindings, one per line").fill("red scarf, visible in every panel\nmap, folded at the corner");
  await page.getByLabel("Action", { exact: true }).fill("The courier raises a hand to knock");
  await page.getByLabel("Background").fill("A stone gate at sunset");
  await page.getByLabel("Composition").fill("Wide view from behind the courier");
  await page.getByLabel("Constraints, one per line").fill("keep the red scarf visible, even when the courier turns\ndo not crop the map, even at the panel edge");
  await page.getByRole("checkbox", {
    name: "I reviewed these exact panel details and confirm them."
  }).check();
}

test("confirms explicit storyboard input once and reloads the persisted LocalFile result", async ({ page, request }) => {
  const projectId = "v7-17-explicit-confirmation-real-e2e";
  const pageUrl = await createReviewedPage(request, projectId);
  const confirmationPath = `/api/projects/${projectId}/pages/1/storyboard/confirm`;
  let confirmationPosts = 0;

  page.on("request", (browserRequest) => {
    if (browserRequest.method() === "POST" && new URL(browserRequest.url()).pathname === confirmationPath) {
      confirmationPosts += 1;
    }
  });

  await page.goto(`/projects/${projectId}/pages/1`);
  await expect(page.getByRole("heading", { name: "Confirm storyboard input" })).toBeVisible();
  await fillAndConfirm(page);

  const confirmation = page.waitForResponse((response) =>
    response.request().method() === "POST"
    && new URL(response.url()).pathname === confirmationPath
  );
  await page.getByRole("button", { name: "Confirm storyboard" }).click();
  const response = await confirmation;
  expect(response.status(), await response.text()).toBe(200);
  expect(await response.json()).toEqual({ status: "storyboarded" });
  await expect(page.getByText("Storyboarded", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Confirm storyboard input" })).toHaveCount(0);
  expect(confirmationPosts).toBe(1);

  await page.reload();
  await expect(page.getByText("Storyboarded", { exact: true })).toBeVisible();

  const persisted = await request.get(pageUrl);
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
  expect(confirmationPosts).toBe(1);
});

test("shows a browser-simulated stale-source conflict and does not retry the confirmation", async ({ page, request }) => {
  const projectId = "v7-17-explicit-conflict-real-e2e";
  await createReviewedPage(request, projectId);
  const confirmationPath = `/api/projects/${projectId}/pages/1/storyboard/confirm`;
  let confirmationPosts = 0;

  page.on("request", (browserRequest) => {
    if (browserRequest.method() === "POST" && new URL(browserRequest.url()).pathname === confirmationPath) {
      confirmationPosts += 1;
    }
  });
  await page.route(`**${confirmationPath}`, async (route) => {
    await route.fulfill({
      status: 409,
      contentType: "application/json",
      body: JSON.stringify({ code: "confirmation_conflict", message: "The Page source changed." })
    });
  });

  await page.goto(`/projects/${projectId}/pages/1`);
  await expect(page.getByRole("heading", { name: "Confirm storyboard input" })).toBeVisible();
  await fillAndConfirm(page);
  const responsePromise = page.waitForResponse((response) =>
    response.request().method() === "POST"
    && new URL(response.url()).pathname === confirmationPath
  );
  await page.getByRole("button", { name: "Confirm storyboard" }).click();
  expect((await responsePromise).status()).toBe(409);
  await expect(page.getByText("The Page source changed. Reload it, review the current source, and confirm again deliberately.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Reload before trying again" })).toBeDisabled();
  expect(confirmationPosts).toBe(1);
});

test("shows a browser-simulated uncertain 503 result and does not retry the confirmation", async ({ page, request }) => {
  const projectId = "v7-17-explicit-uncertain-real-e2e";
  await createReviewedPage(request, projectId);
  const confirmationPath = `/api/projects/${projectId}/pages/1/storyboard/confirm`;
  let confirmationPosts = 0;

  page.on("request", (browserRequest) => {
    if (browserRequest.method() === "POST" && new URL(browserRequest.url()).pathname === confirmationPath) {
      confirmationPosts += 1;
    }
  });
  await page.route(`**${confirmationPath}`, async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ code: "activation_unavailable", message: "The result may be uncertain." })
    });
  });

  await page.goto(`/projects/${projectId}/pages/1`);
  await expect(page.getByRole("heading", { name: "Confirm storyboard input" })).toBeVisible();
  await fillAndConfirm(page);
  const responsePromise = page.waitForResponse((response) =>
    response.request().method() === "POST"
    && new URL(response.url()).pathname === confirmationPath
  );
  await page.getByRole("button", { name: "Confirm storyboard" }).click();
  expect((await responsePromise).status()).toBe(503);
  await expect(page.getByText("The result may be uncertain. Reload the Page and inspect its state before taking another action.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Reload before trying again" })).toBeDisabled();
  expect(confirmationPosts).toBe(1);
});
