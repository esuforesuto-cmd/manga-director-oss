import { spawn } from "node:child_process";
import { unlinkSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const next = fileURLToPath(new URL("../node_modules/next/dist/bin/next", import.meta.url));
const envFile = fileURLToPath(new URL("../.env.local", import.meta.url));
writeFileSync(envFile, "NEXT_PUBLIC_MANGA_DIRECTOR_API_URL=http://127.0.0.1:4010\n");
const child = spawn(process.execPath, [next, "dev"], {
  env: { ...process.env, NEXT_PUBLIC_MANGA_DIRECTOR_API_URL: "http://127.0.0.1:4010" },
  stdio: "inherit"
});

function stop(signal) {
  try { unlinkSync(envFile); } catch { /* Already cleaned up. */ }
  child.kill(signal);
}

for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => stop(signal));
child.on("exit", (code) => {
  try { unlinkSync(envFile); } catch { /* Already cleaned up. */ }
  process.exit(code ?? 1);
});
