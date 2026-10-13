import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";

const apiPort = "8000";
const temporaryRoot = mkdtempSync(join(process.cwd(), ".manga-director-real-e2e-"));
const configPath = join(temporaryRoot, "config.yaml");
const executable = process.platform === "win32" ? "manga-director.exe" : "manga-director";
const environment: NodeJS.ProcessEnv = { ...process.env };
for (const name of Object.keys(environment)) {
  if (name.startsWith("MANGA_DIRECTOR__")) delete environment[name];
}
environment.MANGA_DIRECTOR_PROFILE = "offline";
environment.MANGA_DIRECTOR__REPOSITORY__ROOT = join(temporaryRoot, "repository");
const child = spawn(
  executable,
  ["api", "serve", "--config", configPath, "--port", apiPort],
  {
    env: environment,
    stdio: "inherit"
  }
);

let stopping = false;

function cleanup(): void {
  rmSync(temporaryRoot, { force: true, recursive: true });
}

function stop(signal: NodeJS.Signals): void {
  if (stopping) return;
  stopping = true;
  child.kill(signal);
}

for (const signal of ["SIGINT", "SIGTERM"] as const) {
  process.once(signal, () => stop(signal));
}

child.once("error", (error) => {
  console.error(`Unable to start the real workflow API: ${error.message}`);
  cleanup();
  process.exit(1);
});

child.once("exit", (code, signal) => {
  cleanup();
  if (signal && stopping) process.exit(0);
  process.exit(code ?? 1);
});
