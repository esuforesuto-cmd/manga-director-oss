import { createServer } from "node:http";
import { Buffer } from "node:buffer";

let projectCreated = false;
let pageState = "Draft";
const png = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=", "base64");

const nextState = {
  Draft: { design: "Designed" },
  Designed: { review: "Reviewed" },
  Reviewed: { storyboard: "Storyboarded" },
  Storyboarded: { prompt: "PromptBuilt" },
  PromptBuilt: { generate: "Generated" },
  Generated: { quality: "QualityChecked" },
  QualityChecked: { approve: "Approved" }
};

function availableActions() {
  return Object.keys(nextState[pageState] ?? {});
}

function page() {
  return {
    pageNumber: 1,
    state: pageState,
    qualityPassed: pageState === "QualityChecked" || pageState === "Approved" ? true : null,
    approved: pageState === "Approved",
    workflow: {
      currentState: pageState,
      currentStep: availableActions()[0] ?? null,
      completedSteps: [],
      availableActions: availableActions(),
      history: []
    },
    input: { page_number: 1 },
    artifacts: {
      storyboard: pageState === "Draft" ? null : { persisted: true },
      ...(pageState === "Generated" || pageState === "QualityChecked" || pageState === "Approved"
        ? { image: { artifact_kind: "logical_output_asset", output_asset_id: "asset:demo:001" } }
        : {})
    },
    messages: [],
    errors: [],
    executionTimeMs: 1,
    approvalRequired: pageState === "QualityChecked"
  };
}

function project() {
  return {
    id: "demo",
    title: "Demo manga",
    currentState: pageState,
    updatedAt: "2026-07-25T00:00:00Z",
    progress: { completed: pageState === "Approved" ? 1 : 0, total: 1 },
    currentChapter: "chapter-1",
    currentPage: 1,
    chapters: [{ id: "chapter-1", title: "Chapter 1", pageCount: 1, approvedPages: pageState === "Approved" ? 1 : 0 }],
    workflow: { currentState: pageState, currentStep: availableActions()[0] ?? null, completedSteps: [], availableActions: [], history: [] }
  };
}

function json(response, status, body, headers = {}) {
  response.writeHead(status, {
    "access-control-allow-origin": "http://127.0.0.1:3000",
    "content-type": "application/json",
    ...headers
  });
  response.end(JSON.stringify(body));
}

async function requestBody(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

createServer(async (request, response) => {
  const pathname = new URL(request.url ?? "/", "http://localhost").pathname;
  if (request.method === "OPTIONS") {
    response.writeHead(204, {
      "access-control-allow-origin": "http://127.0.0.1:3000",
      "access-control-allow-headers": "content-type",
      "access-control-allow-methods": "GET, POST, OPTIONS"
    });
    return response.end();
  }
  if (request.method === "GET" && pathname === "/health") return json(response, 200, { status: "ok" });
  if (request.method === "GET" && pathname === "/projects") {
    return json(response, 200, projectCreated ? [project()] : []);
  }
  if (request.method === "POST" && pathname === "/projects") {
    projectCreated = true;
    pageState = "Draft";
    return json(response, 201, project());
  }
  if (request.method === "GET" && pathname === "/projects/demo") return json(response, 200, project());
  if (request.method === "GET" && pathname === "/projects/demo/pages/1") return json(response, 200, page());
  if (request.method === "GET" && pathname === "/projects/demo/pages/1/generated-asset") {
    response.writeHead(200, {
      "access-control-allow-origin": "http://127.0.0.1:3000",
      "cache-control": "no-store",
      "content-type": "image/png",
      "x-content-type-options": "nosniff"
    });
    return response.end(png);
  }
  if (request.method === "GET" && pathname === "/projects/demo/pages/1/approved-asset-download") {
    if (pageState !== "Approved") {
      return json(response, 404, { code: "not_found", message: "Not found." });
    }
    response.writeHead(200, {
      "cache-control": "no-store",
      "content-disposition": "attachment; filename=\"page-1.png\"",
      "content-type": "image/png",
      "x-content-type-options": "nosniff"
    });
    return response.end(png);
  }
  if (request.method === "POST" && pathname === "/projects/demo/pages/1/visual-review-readiness") {
    const body = await requestBody(request);
    const complete = body.reviewerId
      && body.reviewedAt
      && body.overallJudgment
      && body.rationale
      && Array.isArray(body.checklist)
      && body.checklist.length === 18;
    if (!complete) return json(response, 422, { code: "invalid_input", message: "Request validation failed." });
    const ready = pageState === "QualityChecked";
    return json(response, 200, {
      status: ready ? "ready" : "needs_review",
      ready,
      pageState,
      findings: ready ? [] : [{ code: "QUALITY_CHECK_REQUIRED", status: "needs_review", message: "Quality review required.", criterion: "" }],
      missingPrerequisites: ready ? [] : ["QUALITY_CHECK_REQUIRED"],
      analysisOnly: true
    }, {
      "cache-control": "no-store",
      "x-content-type-options": "nosniff"
    });
  }

  const action = pathname.match(/^\/projects\/demo\/pages\/1\/([a-z_]+)$/)?.[1];
  if (request.method === "POST" && action) {
    const target = nextState[pageState]?.[action];
    if (!target) return json(response, 409, { code: "invalid_state", message: "Invalid workflow action." });
    pageState = target;
    return json(response, 200, page());
  }
  return json(response, 404, { code: "not_found", message: "Not found." });
}).listen(4010, "127.0.0.1");
