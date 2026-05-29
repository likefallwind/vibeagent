import { randomUUID } from "node:crypto";
import { mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

export type RunWorkspace = {
  root: string;
  runId: string;
};

export async function createRunWorkspace(baseDir = process.cwd(), runId = makeRunId()): Promise<RunWorkspace> {
  const root = path.resolve(baseDir, ".vibeagent", "runs", runId);
  await mkdir(root, { recursive: true });
  return { root, runId };
}

export function resolveInsideRun(root: string, relativePath: string): string {
  if (!relativePath || relativePath.trim() === "") {
    throw new Error("Path must not be empty.");
  }

  if (path.isAbsolute(relativePath)) {
    throw new Error(`Absolute paths are not allowed: ${relativePath}`);
  }

  const normalized = path.normalize(relativePath);
  if (normalized === ".." || normalized.startsWith(`..${path.sep}`)) {
    throw new Error(`Path escapes the run directory: ${relativePath}`);
  }

  const resolvedRoot = path.resolve(root);
  const resolvedPath = path.resolve(resolvedRoot, normalized);
  if (resolvedPath !== resolvedRoot && !resolvedPath.startsWith(`${resolvedRoot}${path.sep}`)) {
    throw new Error(`Path escapes the run directory: ${relativePath}`);
  }

  return resolvedPath;
}

export async function writeRunFile(workspace: RunWorkspace, relativePath: string, content: string): Promise<string> {
  const target = resolveInsideRun(workspace.root, relativePath);
  await mkdir(path.dirname(target), { recursive: true });
  await writeFile(target, content, "utf8");
  return target;
}

export async function readWorkspaceSnapshot(workspace: RunWorkspace, maxBytes = 12_000): Promise<string> {
  const files = await listFiles(workspace.root);
  if (files.length === 0) {
    return "No files have been written yet.";
  }

  let used = 0;
  const chunks: string[] = [];
  for (const file of files.slice(0, 30)) {
    const absolutePath = resolveInsideRun(workspace.root, file);
    const content = await readFile(absolutePath, "utf8");
    const remaining = maxBytes - used;
    if (remaining <= 0) {
      chunks.push("\n[workspace snapshot truncated]");
      break;
    }

    const shown = content.slice(0, remaining);
    used += shown.length;
    chunks.push(`--- ${file} ---\n${shown}`);
    if (shown.length < content.length) {
      chunks.push("[file truncated]");
      break;
    }
  }

  return chunks.join("\n\n");
}

async function listFiles(root: string, subdir = ""): Promise<string[]> {
  const dir = path.join(root, subdir);
  const entries = await readdir(dir, { withFileTypes: true });
  const files: string[] = [];

  for (const entry of entries) {
    const relativePath = path.join(subdir, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await listFiles(root, relativePath)));
    } else if (entry.isFile()) {
      files.push(toPosixPath(relativePath));
    }
  }

  return files.sort();
}

function makeRunId(): string {
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  return `${timestamp}-${randomUUID().slice(0, 8)}`;
}

function toPosixPath(value: string): string {
  return value.split(path.sep).join("/");
}
