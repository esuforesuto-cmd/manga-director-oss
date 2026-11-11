import { execFileSync, spawn, type ChildProcess } from "node:child_process";
import { cpSync, existsSync, mkdtempSync, rmSync } from "node:fs";
import { createServer, type Server } from "node:http";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

const chromePath = "C:/Program Files/Google/Chrome/Application/chrome.exe";
if (process.platform === "win32" && existsSync(chromePath)) {
  test.use({ launchOptions: { executablePath: chromePath, headless: true } });
}

let apiServer: Server;
let nextProcess: ChildProcess;
let isolatedWebRoot = "";
let appUrl = "";
let confirmationRequests = 0;
let nextStdout = "";
let nextStderr = "";
let nextSpawnErrorCode = "";
let lastHttpStatus: number | null = null;
let lastFailure = "no_response_received";
let updateLatestPageSource: (source: string) => void = () => {};
let submittedExpectedSource: { state: string; page_design: Record<string, unknown>; review: Record<string, unknown> } | null = null;
let submittedPanelValues: Array<{
  characters: string[];
  continuity_bindings: string[];
  constraints: string[];
}> = [];

const maxCapturedOutputChars = 8_000;

function appendBoundedOutput(current: string, chunk: Buffer): string {
  return (current + chunk.toString("utf8")).slice(-maxCapturedOutputChars);
}

function safeOutputSummary(output: string): string {
  const safeLines = output.split(/\r?\n/).flatMap((line) => {
    if (/^\s*> next dev\s*$/.test(line)) return ["> next dev"];
    if (/^\s*▲ Next\.js [\d.]+\s*$/.test(line)) return ["▲ Next.js started"];
    if (/^\s*[-✓] Ready in [\d.]+\s*(?:ms|s)\s*$/.test(line)) return ["Ready message observed"];
    if (/^\s*○ Compiling \/projects\/(?:demo|\[projectId\])\/pages\/(?:1|\[pageNumber\])(?:\/page)?(?: \(\/projects\/demo\/pages\/1\))?\s*\.\.\.\s*$/.test(line)) return ["Target page compilation started"];
    if (/^\s*✓ Compiled \/projects\/(?:demo|\[projectId\])\/pages\/(?:1|\[pageNumber\])(?:\/page)? in [\d.]+\s*(?:ms|s)(?: \(\d+ modules\))?\s*$/.test(line)) return ["Target page compilation completed"];
    if (/EADDRINUSE/.test(line)) return ["Startup error category: address already in use"];
    if (/ERR_MODULE_NOT_FOUND|Cannot find module/.test(line)) return ["Startup error category: module unavailable"];
    if (/Module not found/.test(line)) return ["Compilation error category: module unavailable"];
    if (/Failed to compile|Build Error/.test(line)) return ["Compilation error category: compilation failed"];
    if (/SyntaxError/.test(line)) return ["Compilation error category: syntax error"];
    if (/TypeError/.test(line)) return ["Runtime error category: type error"];
    return [];
  });
  return safeLines.length ? safeLines.join("; ") : output.length ? "[captured output withheld by safety filter]" : "[no output captured]";
}

function serverDiagnostics(reason: string, lastHttpStatus: number | null, lastFailure: string): string {
  const processState = !nextProcess
    ? "not started"
    : nextProcess.exitCode !== null
      ? `exited with code ${nextProcess.exitCode}`
      : nextProcess.signalCode !== null
        ? `exited with signal ${nextProcess.signalCode}`
        : "still running";
  const spawnError = nextSpawnErrorCode ? `; spawn error code ${nextSpawnErrorCode}` : "";
  return [
    `${reason} (process ${processState}${spawnError}; last HTTP status ${lastHttpStatus ?? "none"}; last readiness probe ${lastFailure})`,
    `Child output (bounded to ${maxCapturedOutputChars} characters per stream): stdout=${safeOutputSummary(nextStdout)}; stderr=${safeOutputSummary(nextStderr)}`
  ].join(". ");
}

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
  updateLatestPageSource = (source: string) => {
    pageDetail = {
      ...pageDetail,
      artifacts: {
        ...pageDetail.artifacts,
        pageDesign: { page_purpose: source }
      }
    };
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
    filter: (source) => !["node_modules", ".next", ".git", "e2e", "e2e-real", "tests", "test-results", "playwright-report"].includes(source.split(/[\\/]/).at(-1) ?? "")
  });
  cpSync(join(sourceWebRoot, "node_modules"), join(isolatedWebRoot, "node_modules"), { recursive: true });

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
    stdio: ["ignore", "pipe", "pipe"]
  });
  nextProcess.stdout?.on("data", (chunk: Buffer) => { nextStdout = appendBoundedOutput(nextStdout, chunk); });
  nextProcess.stderr?.on("data", (chunk: Buffer) => { nextStderr = appendBoundedOutput(nextStderr, chunk); });
  nextProcess.once("error", (error: NodeJS.ErrnoException) => {
    const code = error.code;
    nextSpawnErrorCode = code && ["ENOENT", "EACCES", "EPERM", "EADDRINUSE", "UNKNOWN"].includes(code) ? code : "other";
  });

  const deadline = Date.now() + 50_000;
  while (Date.now() < deadline) {
    if (nextProcess.exitCode !== null || nextProcess.signalCode !== null) {
      throw new Error(serverDiagnostics("Isolated Next.js server stopped before readiness", lastHttpStatus, lastFailure));
    }
    try {
      const requestTimeoutMs = Math.max(1, deadline - Date.now());
      const response = await fetch(`${appUrl}/projects/demo/pages/1`, {
        signal: AbortSignal.timeout(requestTimeoutMs)
      });
      lastHttpStatus = response.status;
      if (!response.ok) {
        lastFailure = "http_response_not_successful";
      } else if ((await response.text()).includes("Confirm storyboard input")) {
        lastFailure = "readiness_confirmed";
        return;
      } else {
        lastFailure = "expected_page_text_missing";
      }
    } catch (error) {
      lastFailure = error instanceof Error && error.name === "TimeoutError"
        ? "request_timeout"
        : error instanceof TypeError
          ? "request_type_error"
          : error instanceof Error
            ? "request_error"
            : "request_failed";
    }
    const delayMs = Math.min(250, Math.max(0, deadline - Date.now()));
    if (delayMs > 0) await new Promise((resolveDelay) => setTimeout(resolveDelay, delayMs));
  }
  throw new Error(serverDiagnostics("Isolated Next.js server did not become ready within 50 seconds", lastHttpStatus, lastFailure));
});

test.afterEach(async ({}, testInfo) => {
  if (testInfo.status === testInfo.expectedStatus) return;
  await testInfo.attach("server-diagnostics.txt", {
    body: serverDiagnostics("Post-readiness browser test failed", lastHttpStatus, lastFailure),
    contentType: "text/plain"
  });
});

test.afterAll(async () => {
  if (nextProcess && nextProcess.exitCode === null && nextProcess.signalCode === null) {
    if (process.platform === "win32" && nextProcess.pid !== undefined) {
      try {
        execFileSync("taskkill.exe", ["/PID", String(nextProcess.pid), "/T", "/F"], { stdio: "ignore" });
      } catch (error) {
        if (nextProcess.exitCode === null && nextProcess.signalCode === null) throw error;
      }
    } else {
      nextProcess.kill("SIGTERM");
    }
    if (nextProcess.exitCode === null && nextProcess.signalCode === null) await new Promise<void>((resolveExit, rejectExit) => {
      const timeout = setTimeout(resolveExit, 5_000);
      nextProcess.once("exit", () => { clearTimeout(timeout); resolveExit(); });
      nextProcess.once("error", (error) => { clearTimeout(timeout); rejectExit(error); });
    });
    if (nextProcess.exitCode === null && nextProcess.signalCode === null) throw new Error("Isolated Next.js process did not exit; preserving its temporary root.");
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
      const body = route.request().postDataJSON() as {
        panels: typeof submittedPanelValues;
        expectedSource: typeof submittedExpectedSource;
      };
      submittedPanelValues = body.panels;
      submittedExpectedSource = body.expectedSource;
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
  await page.getByLabel("Panel count").selectOption("2");
  await fillStoryboardPanel(page, 0);
  await fillStoryboardPanel(page, 1);
  await confirmation.check();
  const conflictResponse = page.waitForResponse((response) =>
    response.request().method() === "POST" && new URL(response.url()).pathname === confirmationPath
  );
  await submit.click();
  expect((await conflictResponse).status()).toBe(409);
  await expect(page.getByText(/Page source changed/)).toBeVisible();
  const loadLatest = page.getByRole("button", { name: "Load latest state" });
  await expect(loadLatest).toBeEnabled();
  await expect(page.getByRole("button", { name: "Reload before trying again" })).toBeDisabled();
  expect(browserPosts).toHaveLength(2);
  expect(browserPosts[1]).toEqual({ method: "POST", url: `${appUrl}${confirmationPath}` });

  updateLatestPageSource("Latest source from server after conflict.");
  const refreshedPage = page.waitForNavigation();
  await loadLatest.click();
  await refreshedPage;
  await page.getByText("Reviewed source captured for this confirmation").click();
  const refreshedPageDesign = page.locator("details pre").first();
  await expect(refreshedPageDesign).toBeVisible();
  await expect(refreshedPageDesign).toContainText("Latest source from server after conflict.");
  await expect(confirmation).not.toBeChecked();
  await expect(page.getByLabel("Panel count")).toHaveValue("1");
  await expect(page.getByLabel("Narrative intent")).toHaveValue("");
  expect(browserPosts).toHaveLength(2);

  nextOutcome = "success";
  await fillStoryboardPanel(page);
  await confirmation.check();
  const refreshedSourceResponse = page.waitForResponse((response) =>
    response.request().method() === "POST" && new URL(response.url()).pathname === confirmationPath
  );
  await submit.click();
  expect((await refreshedSourceResponse).status()).toBe(200);
  expect(submittedExpectedSource).toEqual({
    state: "Reviewed",
    page_design: { page_purpose: "Latest source from server after conflict." },
    review: { decision: "Ready for an explicit storyboard." }
  });
  expect(browserPosts).toHaveLength(3);

  nextOutcome = "uncertain";
  await page.reload();
  await fillStoryboardPanel(page);
  await confirmation.check();
  await submit.click();
  await expect(page.getByText("The result may be uncertain. Reload the Page and inspect its state before taking another action.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Reload before trying again" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Load latest state" })).toHaveCount(0);
  expect(browserPosts).toHaveLength(4);
  expect(browserPosts[3]).toEqual({ method: "POST", url: `${appUrl}${confirmationPath}` });
});
