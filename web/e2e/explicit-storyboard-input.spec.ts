import { execFileSync, spawn, type ChildProcess } from "node:child_process";
import { cpSync, existsSync, mkdtempSync, rmSync, symlinkSync } from "node:fs";
import { createServer, type Server } from "node:http";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

const chromePath = "C:/Program Files/Google/Chrome/Application/chrome.exe";
test.use({ launchOptions: { executablePath: chromePath, headless: true } });

let apiServer: Server;
let nextProcess: ChildProcess;
let isolatedWebRoot = "";
let appUrl = "";
let confirmationRequests = 0;
let submittedPanelValues: Array<{
  characters: string[];
  continuity_bindings: string[];
  constraints: string[];
}> = [];

async function fillStoryboardPanel(page: Page, index = 0): Promise<void> {
  await page.getByLabel("Narrative intent").nth(index).fill("The courier waits beneath the station clock.");
  await page.getByLabel("Character IDs, comma separated").nth(index).fill("courier-1, station-clerk");
  await page.getByLabel("Continuity bindings, one per line").nth(index).fill("blue coat, visible in the window\nmap, folded at the corner");
  await page.getByRole("textbox", { name: "Action" }).nth(index).fill("The courier checks the timetable.");
  await page.getByLabel("Background").nth(index).fill("A small station at dusk.");
  await page.getByLabel("Composition").nth(index).fill("The clock frames the waiting courier.");
  await page.getByLabel("Constraints, one per line").nth(index).fill("No readable text, including signs.\nKeep the map, even near the edge.");
}

function listen(server: Server): Promise<number> {
  return new Promise((resolveListen, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (!address || typeof address === "string") return reject(new Error("Local test server did not bind."));
      resolveListen(address.port);
    });
  });
}

async function availablePort(): Promise<number> {
  const server = createServer();
  const port = await listen(server);
  await new Promise<void>((resolveClose, reject) => server.close((error) => error ? reject(error) : resolveClose()));
  return port;
}

test.beforeAll(async () => {
  test.setTimeout(120_000);
  if (!existsSync(chromePath)) throw new Error("The installed Chrome executable is unavailable.");

  let pageDetail = {
    pageNumber: 1,
    state: "Reviewed",
    qualityPassed: null,
    approved: false,
    workflow: { currentState: "Reviewed", currentStep: null, completedSteps: [], availableActions: [], history: [] },
    input: { page_number: 1 },
    artifacts: {
      pageDesign: { page_purpose: "A courier reaches a quiet station." },
      review: { decision: "Ready for an explicit storyboard." }
    },
    messages: [],
    errors: [],
    executionTimeMs: 1,
    approvalRequired: false
  };

  apiServer = createServer((request, response) => {
    const pathname = new URL(request.url ?? "/", "http://127.0.0.1").pathname;
    response.setHeader("content-type", "application/json");
    if (request.method === "GET" && pathname === "/projects/demo/pages/1") {
      response.writeHead(200).end(JSON.stringify(pageDetail));
      return;
    }
    if (request.method === "POST" && pathname === "/projects/demo/pages/1/storyboard/confirm") {
      confirmationRequests += 1;
      response.writeHead(200).end(JSON.stringify({ status: "storyboarded" }));
      return;
    }
    response.writeHead(404).end(JSON.stringify({ code: "not_found", message: "Not found." }));
  });
  const apiPort = await listen(apiServer);

  const sourceWebRoot = resolve(process.cwd());
  isolatedWebRoot = mkdtempSync(join(tmpdir(), "manga-director-ui-e2e-"));
  cpSync(sourceWebRoot, isolatedWebRoot, {
    recursive: true,
    filter: (source) => !["node_modules", ".next", ".git", "e2e", "e2e-real", "tests"].includes(source.split(/[\\/]/).at(-1) ?? "")
  });
  symlinkSync(join(sourceWebRoot, "node_modules"), join(isolatedWebRoot, "node_modules"), "junction");

  const appPort = await availablePort();
  appUrl = `http://127.0.0.1:${appPort}`;
  nextProcess = spawn(process.execPath, [
    join(isolatedWebRoot, "node_modules", "next", "dist", "bin", "next"),
    "dev", "--hostname", "127.0.0.1", "--port", String(appPort)
  ], {
    cwd: isolatedWebRoot,
    env: {
      ...process.env,
      NEXT_PUBLIC_MANGA_DIRECTOR_API_URL: `http://127.0.0.1:${apiPort}`,
      MANGA_DIRECTOR_API_URL: `http://127.0.0.1:${apiPort}`
    },
    stdio: "ignore"
  });

  const deadline = Date.now() + 50_000;
  while (Date.now() < deadline) {
    if (nextProcess.exitCode !== null) throw new Error(`Isolated Next.js server exited (${nextProcess.exitCode}).`);
    try {
      const response = await fetch(`${appUrl}/projects/demo/pages/1`);
      if (response.ok && (await response.text()).includes("Confirm storyboard input")) return;
    } catch {
      // The isolated development server is still starting.
    }
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 250));
  }
  throw new Error("Isolated Next.js server did not become ready in time.");
});

test.afterAll(async () => {
  if (nextProcess && nextProcess.exitCode === null) {
    if (process.platform === "win32" && nextProcess.pid !== undefined) {
      try {
        execFileSync("taskkill.exe", ["/PID", String(nextProcess.pid), "/T", "/F"], { stdio: "ignore" });
      } catch (error) {
        if (nextProcess.exitCode === null) throw error;
      }
    } else {
      nextProcess.kill("SIGTERM");
    }
    if (nextProcess.exitCode === null) await new Promise<void>((resolveExit, rejectExit) => {
      const timeout = setTimeout(resolveExit, 5_000);
      nextProcess.once("exit", () => { clearTimeout(timeout); resolveExit(); });
      nextProcess.once("error", (error) => { clearTimeout(timeout); rejectExit(error); });
    });
    if (nextProcess.exitCode === null) throw new Error("Isolated Next.js process did not exit; preserving its temporary root.");
  }
  if (apiServer?.listening) await new Promise<void>((resolveClose) => apiServer.close(() => resolveClose()));
  if (isolatedWebRoot) rmSync(isolatedWebRoot, { recursive: true, force: true });
});

test("editing or changing panel count revokes confirmation and prevents submission", async ({ page }) => {
  confirmationRequests = 0;
  submittedPanelValues = [];
  await page.goto(`${appUrl}/projects/demo/pages/1`);
  const submit = page.getByRole("button", { name: "Confirm storyboard" });
  const confirmation = page.getByRole("checkbox", { name: "I reviewed these exact panel details and confirm them." });
  const confirmationPath = "/api/projects/demo/pages/1/storyboard/confirm";
  const browserPosts: Array<{ method: string; url: string }> = [];
  let nextOutcome: "success" | "conflict" | "uncertain" = "success";

  page.on("request", (request) => {
    if (new URL(request.url()).pathname === confirmationPath && request.method() === "POST") {
      browserPosts.push({ method: request.method(), url: request.url() });
    }
  });
  await page.route(`**${confirmationPath}`, async (route) => {
    if (route.request().method() !== "POST") {
      await route.continue();
      return;
    }
    if (nextOutcome === "uncertain") {
      await route.abort("failed");
      return;
    }
    if (nextOutcome === "conflict") {
      await route.fulfill({
        status: 409,
        contentType: "application/json",
        body: JSON.stringify({ code: "confirmation_conflict", message: "The Page source changed." })
      });
      return;
    }
    if (nextOutcome === "success") {
      const body = route.request().postDataJSON() as { panels: typeof submittedPanelValues };
      submittedPanelValues = body.panels;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "storyboarded" })
    });
  });

  await fillStoryboardPanel(page);

  await confirmation.check();
  await expect(submit).toBeEnabled();
  await page.getByRole("textbox", { name: "Action" }).fill("The courier folds the timetable.");
  await expect(confirmation).not.toBeChecked();
  await expect(submit).toBeDisabled();
  await submit.evaluate((button) => (button as HTMLButtonElement).click());
  expect(confirmationRequests).toBe(0);
  expect(browserPosts).toEqual([]);

  await confirmation.check();
  await expect(submit).toBeEnabled();
  await page.getByLabel("Panel count").selectOption("2");
  await expect(confirmation).not.toBeChecked();
  await expect(submit).toBeDisabled();
  await submit.evaluate((button) => (button as HTMLButtonElement).click());
  expect(confirmationRequests).toBe(0);
  expect(browserPosts).toEqual([]);

  await fillStoryboardPanel(page, 1);
  await confirmation.check();
  const successResponse = page.waitForResponse((response) =>
    response.request().method() === "POST" && new URL(response.url()).pathname === confirmationPath
  );
  await submit.click();
  expect((await successResponse).status()).toBe(200);
  await expect(page.getByText("Storyboard saved. Reload the page to inspect the result.")).toBeVisible();
  expect(browserPosts).toEqual([{ method: "POST", url: `${appUrl}${confirmationPath}` }]);
  expect(submittedPanelValues.map(({ characters, continuity_bindings, constraints }) => ({
    characters,
    continuity_bindings,
    constraints
  }))).toEqual([
    {
      characters: ["courier-1", "station-clerk"],
      continuity_bindings: ["blue coat, visible in the window", "map, folded at the corner"],
      constraints: ["No readable text, including signs.", "Keep the map, even near the edge."]
    },
    {
      characters: ["courier-1", "station-clerk"],
      continuity_bindings: ["blue coat, visible in the window", "map, folded at the corner"],
      constraints: ["No readable text, including signs.", "Keep the map, even near the edge."]
    }
  ]);

  nextOutcome = "conflict";
  await page.reload();
  await fillStoryboardPanel(page);
  await confirmation.check();
  const conflictResponse = page.waitForResponse((response) =>
    response.request().method() === "POST" && new URL(response.url()).pathname === confirmationPath
  );
  await submit.click();
  expect((await conflictResponse).status()).toBe(409);
  await expect(page.getByText(/Page source changed/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Reload before trying again" })).toBeDisabled();
  expect(browserPosts).toHaveLength(2);
  expect(browserPosts[1]).toEqual({ method: "POST", url: `${appUrl}${confirmationPath}` });

  nextOutcome = "uncertain";
  await page.reload();
  await fillStoryboardPanel(page);
  await confirmation.check();
  await submit.click();
  await expect(page.getByText("The result may be uncertain. Reload the Page and inspect its state before taking another action.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Reload before trying again" })).toBeDisabled();
  expect(browserPosts).toHaveLength(3);
  expect(browserPosts[2]).toEqual({ method: "POST", url: `${appUrl}${confirmationPath}` });
});
