import { spawn } from "node:child_process";
import type { AgentAction, CommandResult, ModelActionResponse, Observation } from "./types.js";
import type { RunWorkspace } from "./workspace.js";
import { writeRunFile } from "./workspace.js";

export class ActionParseError extends Error {
  constructor(message: string, readonly raw: string) {
    super(message);
    this.name = "ActionParseError";
  }
}

export function parseModelAction(raw: string): ModelActionResponse {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (error) {
    throw new ActionParseError(`Model output was not valid JSON: ${(error as Error).message}`, raw);
  }

  if (!isRecord(parsed)) {
    throw new ActionParseError("Model output must be a JSON object.", raw);
  }

  const thought = parsed.thought;
  if (typeof thought !== "string") {
    throw new ActionParseError("Model output must include a string thought.", raw);
  }

  const action = parseAction(parsed.action, raw);
  return { thought, action };
}

export async function executeAction(
  workspace: RunWorkspace,
  action: AgentAction,
  commandTimeoutMs = 30_000,
): Promise<Observation> {
  if (action.type === "write_file") {
    await writeRunFile(workspace, action.path, action.content);
    return {
      kind: "write_file",
      path: action.path,
      ok: true,
      message: `Wrote ${action.path}`,
    };
  }

  if (action.type === "run_command") {
    return {
      kind: "run_command",
      result: await runCommand(workspace.root, action.command, commandTimeoutMs),
    };
  }

  return {
    kind: "finish",
    message: action.message,
  };
}

export function runCommand(cwd: string, command: string, timeoutMs = 30_000): Promise<CommandResult> {
  return new Promise((resolve) => {
    const child = spawn(command, {
      cwd,
      detached: process.platform !== "win32",
      shell: true,
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";
    let timedOut = false;
    let settled = false;
    let forceKillTimeout: NodeJS.Timeout | undefined;

    const timeout = setTimeout(() => {
      timedOut = true;
      terminateProcess(child.pid, "SIGTERM");
      forceKillTimeout = setTimeout(() => {
        terminateProcess(child.pid, "SIGKILL");
      }, 500);
    }, timeoutMs);

    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk: string) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk: string) => {
      stderr += chunk;
    });

    child.on("error", (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      if (forceKillTimeout) clearTimeout(forceKillTimeout);
      resolve({
        command,
        exitCode: null,
        stdout,
        stderr: `${stderr}${stderr ? "\n" : ""}${error.message}`,
        timedOut,
        signal: null,
      });
    });

    child.on("close", (exitCode, signal) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      if (forceKillTimeout) clearTimeout(forceKillTimeout);
      resolve({
        command,
        exitCode,
        stdout,
        stderr,
        timedOut,
        signal,
      });
    });
  });
}

function terminateProcess(pid: number | undefined, signal: NodeJS.Signals): void {
  if (!pid) return;

  try {
    if (process.platform === "win32") {
      process.kill(pid, signal);
    } else {
      process.kill(-pid, signal);
    }
  } catch {
    try {
      process.kill(pid, signal);
    } catch {
      // Process already exited.
    }
  }
}

function parseAction(value: unknown, raw: string): AgentAction {
  if (!isRecord(value)) {
    throw new ActionParseError("Model output must include an action object.", raw);
  }

  if (value.type === "write_file") {
    if (typeof value.path !== "string") {
      throw new ActionParseError("write_file action requires a string path.", raw);
    }
    if (typeof value.content !== "string") {
      throw new ActionParseError("write_file action requires string content.", raw);
    }
    return {
      type: "write_file",
      path: value.path,
      content: value.content,
    };
  }

  if (value.type === "run_command") {
    if (typeof value.command !== "string" || value.command.trim() === "") {
      throw new ActionParseError("run_command action requires a non-empty command.", raw);
    }
    return {
      type: "run_command",
      command: value.command,
    };
  }

  if (value.type === "finish") {
    if (typeof value.message !== "string") {
      throw new ActionParseError("finish action requires a string message.", raw);
    }
    return {
      type: "finish",
      message: value.message,
    };
  }

  throw new ActionParseError("Unsupported action type.", raw);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
