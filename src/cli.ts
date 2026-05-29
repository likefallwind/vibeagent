#!/usr/bin/env node
import readline from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";
import { runAgent } from "./agent.js";
import { MiniMaxClient } from "./minimax.js";
import type { AgentStatus, Observation } from "./types.js";

async function main(): Promise<void> {
  const rl = readline.createInterface({ input, output });

  console.log("VibeAgent v0.1");
  console.log("Type a programming task. Press Ctrl+C to exit.");

  const client = new MiniMaxClient();

  while (true) {
    const task = (await rl.question("\nvibeagent> ")).trim();
    if (!task) {
      continue;
    }

    try {
      const result = await runAgent(task, {
        client,
        logger: logStatus,
      });

      console.log(result.success ? "\nSuccess" : "\nStopped");
      console.log(result.message);
      console.log(`Run directory: ${result.runDir}`);
      console.log(`Iterations: ${result.iterations}`);
      printCommandSummary(result.observations);
    } catch (error) {
      console.error(`\nError: ${(error as Error).message}`);
    }
  }
}

function logStatus(status: AgentStatus, detail?: string): void {
  console.log(`[${status}]${detail ? ` ${detail}` : ""}`);
}

function printCommandSummary(observations: Observation[]): void {
  const commandObservations = observations.filter((item) => item.kind === "run_command");
  if (commandObservations.length === 0) {
    return;
  }

  console.log("Commands:");
  for (const observation of commandObservations) {
    if (observation.kind !== "run_command") continue;
    const result = observation.result;
    const output = result.stdout.trim() || result.stderr.trim();
    console.log(`- ${result.command} -> exit=${result.exitCode}${result.timedOut ? " timeout" : ""}`);
    if (output) {
      console.log(indent(truncate(output, 800), "  "));
    }
  }
}

function truncate(value: string, maxLength: number): string {
  if (value.length <= maxLength) return value;
  return `${value.slice(0, maxLength)}\n[truncated]`;
}

function indent(value: string, prefix: string): string {
  return value
    .split("\n")
    .map((line) => `${prefix}${line}`)
    .join("\n");
}

main().catch((error: unknown) => {
  console.error((error as Error).message);
  process.exitCode = 1;
});
