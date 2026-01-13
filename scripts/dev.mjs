import { spawn } from "node:child_process";

const children = [];
let shuttingDown = false;

const processes = [
  {
    label: "tailwind",
    command: "npx",
    args: [
      "--yes",
      "@tailwindcss/cli",
      "-i",
      "frontend/css/tailwind.css",
      "-o",
      "frontend/css/output.css",
      "--watch",
    ],
    env: {
      ...process.env,
      TAILWIND_DISABLE_ANALYTICS: "1",
      FORCE_COLOR: process.env.FORCE_COLOR || "1",
    },
  },
  {
    label: "vite",
    command: "npm",
    args: ["run", "dev:vite"],
    env: process.env,
  },
];

function terminate(exitCode = 0) {
  if (shuttingDown) {
    return;
  }
  shuttingDown = true;

  for (const child of children) {
    if (!child.killed) {
      child.kill("SIGINT");
      setTimeout(() => {
        if (!child.killed) {
          child.kill("SIGTERM");
        }
      }, 2000).unref();
    }
  }

  process.exitCode = exitCode;
}

for (const proc of processes) {
  const child = spawn(proc.command, proc.args, {
    env: proc.env,
    stdio: "inherit",
  });

  children.push(child);

  child.on("error", (error) => {
    console.error(`[dev:${proc.label}] failed to start`, error);
    terminate(1);
  });

  child.on("exit", (code, signal) => {
    if (shuttingDown) {
      return;
    }

    const exitSignal = signal ? `signal ${signal}` : `code ${code}`;
    console.error(`[dev:${proc.label}] exited unexpectedly (${exitSignal})`);
    terminate(code ?? 1);
  });
}

const handleShutdown = () => terminate(0);

process.on("SIGINT", handleShutdown);
process.on("SIGTERM", handleShutdown);
