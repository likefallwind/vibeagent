import { ActionParseError, executeAction, parseModelAction } from "./actions.js";
import { buildMessages } from "./prompts.js";
import type { AgentLogger, ChatClient, Observation } from "./types.js";
import { createRunWorkspace, type RunWorkspace } from "./workspace.js";

export type AgentResult = {
  success: boolean;
  message: string;
  runDir: string;
  runId: string;
  iterations: number;
  observations: Observation[];
};

export type RunAgentOptions = {
  client: ChatClient;
  baseDir?: string;
  maxIterations?: number;
  commandTimeoutMs?: number;
  logger?: AgentLogger;
  workspace?: RunWorkspace;
};

export async function runAgent(task: string, options: RunAgentOptions): Promise<AgentResult> {
  const maxIterations = options.maxIterations ?? 5;
  const commandTimeoutMs = options.commandTimeoutMs ?? 30_000;
  const workspace = options.workspace ?? (await createRunWorkspace(options.baseDir));
  const observations: Observation[] = [];

  for (let iteration = 1; iteration <= maxIterations; iteration += 1) {
    options.logger?.("thinking", `iteration ${iteration}/${maxIterations}`);

    const messages = await buildMessages(task, workspace, observations);
    const raw = await options.client.complete(messages);

    let parsed;
    try {
      parsed = parseModelAction(raw);
    } catch (error) {
      if (error instanceof ActionParseError) {
        return {
          success: false,
          message: `Model output was not valid action JSON: ${summarize(error.raw)}`,
          runDir: workspace.root,
          runId: workspace.runId,
          iterations: iteration,
          observations,
        };
      }
      throw error;
    }

    const action = parsed.action;
    if (action.type === "write_file") {
      options.logger?.("writing file", action.path);
    } else if (action.type === "run_command") {
      options.logger?.("running command", action.command);
    }

    const observation = await executeAction(workspace, action, commandTimeoutMs);
    observations.push(observation);

    if (observation.kind === "finish") {
      options.logger?.("finished", observation.message);
      return {
        success: true,
        message: observation.message,
        runDir: workspace.root,
        runId: workspace.runId,
        iterations: iteration,
        observations,
      };
    }

    if (observation.kind === "run_command") {
      const ok = observation.result.exitCode === 0 && !observation.result.timedOut;
      options.logger?.(ok ? "observed success" : "observed failure", summarizeCommand(observation.result));
    }
  }

  return {
    success: false,
    message: `Reached iteration limit (${maxIterations}) before finish.`,
    runDir: workspace.root,
    runId: workspace.runId,
    iterations: maxIterations,
    observations,
  };
}

function summarize(value: string, maxLength = 500): string {
  const compact = value.replace(/\s+/g, " ").trim();
  if (compact.length <= maxLength) return compact;
  return `${compact.slice(0, maxLength)}...`;
}

function summarizeCommand(result: { exitCode: number | null; stdout: string; stderr: string; timedOut: boolean }): string {
  const output = result.stderr || result.stdout || "(no output)";
  return `exit=${result.exitCode} timedOut=${result.timedOut} ${summarize(output, 300)}`;
}
