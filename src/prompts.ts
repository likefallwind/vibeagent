import type { ChatMessage, Observation } from "./types.js";
import type { RunWorkspace } from "./workspace.js";
import { readWorkspaceSnapshot } from "./workspace.js";

export const systemPrompt = `You are VibeAgent, a minimal ReAct coding agent.

You solve the user's programming task by producing exactly one JSON object per turn.
Do not use Markdown, comments outside JSON, or code fences.

Allowed actions:
1. write_file: create or replace a file under the current run directory.
2. run_command: run a command from the current run directory.
3. finish: stop when the task is complete.

All file paths must be relative. Never use absolute paths or "..".
Keep tasks small and concrete. Prefer single-file scripts unless the user asks otherwise.

Required JSON shape:
{
  "thought": "short reasoning summary",
  "action": {
    "type": "write_file | run_command | finish",
    "path": "relative/path.js",
    "content": "...",
    "command": "node relative/path.js",
    "message": "done"
  }
}`;

export async function buildMessages(
  task: string,
  workspace: RunWorkspace,
  observations: Observation[],
): Promise<ChatMessage[]> {
  const snapshot = await readWorkspaceSnapshot(workspace);
  return [
    { role: "system", content: systemPrompt },
    {
      role: "user",
      content: [
        `User task:\n${task}`,
        `Run directory:\n${workspace.root}`,
        `Current files:\n${snapshot}`,
        `Previous observations:\n${formatObservations(observations)}`,
        "Choose the next single action. If a command succeeded and proves the task is done, use finish.",
      ].join("\n\n"),
    },
  ];
}

function formatObservations(observations: Observation[]): string {
  if (observations.length === 0) {
    return "No observations yet.";
  }

  return observations
    .map((observation, index) => {
      if (observation.kind === "write_file") {
        return `${index + 1}. write_file ${observation.path}: ${observation.message}`;
      }

      if (observation.kind === "finish") {
        return `${index + 1}. finish: ${observation.message}`;
      }

      const result = observation.result;
      return [
        `${index + 1}. run_command: ${result.command}`,
        `exitCode: ${result.exitCode}`,
        `timedOut: ${result.timedOut}`,
        `signal: ${result.signal ?? "none"}`,
        `stdout:\n${truncate(result.stdout)}`,
        `stderr:\n${truncate(result.stderr)}`,
      ].join("\n");
    })
    .join("\n\n");
}

function truncate(value: string, maxLength = 4_000): string {
  if (!value) return "";
  if (value.length <= maxLength) return value;
  return `${value.slice(0, maxLength)}\n[truncated]`;
}
