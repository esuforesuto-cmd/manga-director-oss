import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const next = fileURLToPath(new URL("../node_modules/next/dist/bin/next", import.meta.url));
const child = spawn(process.execPath, [next, "dev", "--hostname", "127.0.0.1"], {
  env: { ...process.env, NEXT_PUBLIC_MANGA_DIRECTOR_API_URL: "http://127.0.0.1:4010", MANGA_DIRECTOR_API_URL: "http://127.0.0.1:4010" },
  stdio: "inherit"
});

function stop(signal) {
  child.kill(signal);
}

for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => stop(signal));
child.on("exit", (code) => {
  process.exit(code ?? 1);
});
