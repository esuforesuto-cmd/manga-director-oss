import { expect, test } from "@playwright/test";

test("shows human approval only for a QualityChecked page", async ({ page, request }) => {
  const created = await request.post("http://127.0.0.1:4010/projects", { data: { id: "demo", title: "Demo manga" } });
  expect(created.status()).toBe(201);

  for (const action of ["Design", "Review", "Storyboard", "Build prompt", "Generate", "Quality check"]) {
    const apiAction = { "Build prompt": "prompt", "Quality check": "quality" }[action] ?? action.toLowerCase();
    const response = await request.post(`http://127.0.0.1:4010/projects/demo/pages/1/${apiAction}`);
    expect(response.status()).toBe(200);
  }

  await page.goto("/projects/demo/pages/1");
  await expect(page.getByRole("heading", { name: "Human approval" })).toBeVisible();
});
