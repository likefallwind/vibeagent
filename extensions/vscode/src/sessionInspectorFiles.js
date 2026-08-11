'use strict';

const fs = require('node:fs/promises');
const path = require('node:path');

const MAX_INSPECTED_FILE_BYTES = 10 * 1024 * 1024;
const MAX_INSPECTED_FILES = 100;

async function sessionFileQuickPickItems(root, files, resolver = resolveSessionFilePath) {
  if (!Array.isArray(files) || files.length > MAX_INSPECTED_FILES) {
    throw new Error('VibeAgent returned an invalid inspected file list.');
  }
  const candidates = await Promise.all(files.map(async (file) => {
    try {
      const targetPath = await resolver(root, file.path);
      return {
        label: file.path,
        description: file.uses.length ? file.uses.join(', ') : 'reference',
        detail: boundedDetail(file),
        sourcePath: file.path,
        targetPath,
      };
    } catch (_error) {
      return null;
    }
  }));
  return candidates.filter(Boolean);
}

async function resolveSessionFilePath(root, value, fileSystem = fs) {
  const segments = relativePathSegments(value);
  if (typeof root !== 'string' || !root || root.includes('\0')) {
    throw new Error('The inspected workspace root is invalid.');
  }
  const lexicalRoot = path.resolve(root);
  const lexicalTarget = path.resolve(lexicalRoot, ...segments);
  if (!isStrictDescendant(lexicalRoot, lexicalTarget)) {
    throw new Error('The inspected file is outside the workspace.');
  }
  const [realRoot, realTarget] = await Promise.all([
    fileSystem.realpath(lexicalRoot),
    fileSystem.realpath(lexicalTarget),
  ]);
  if (!isStrictDescendant(realRoot, realTarget)) {
    throw new Error('The inspected file resolves outside the workspace.');
  }
  const stats = await fileSystem.lstat(realTarget);
  if (!stats.isFile()) throw new Error('The inspected path is not a regular file.');
  if (!Number.isSafeInteger(stats.size) || stats.size < 0 || stats.size > MAX_INSPECTED_FILE_BYTES) {
    throw new Error(`The inspected file exceeds ${MAX_INSPECTED_FILE_BYTES} bytes.`);
  }
  const [confirmedRoot, confirmedTarget] = await Promise.all([
    fileSystem.realpath(lexicalRoot),
    fileSystem.realpath(lexicalTarget),
  ]);
  if (confirmedRoot !== realRoot || confirmedTarget !== realTarget) {
    throw new Error('The inspected file changed during validation.');
  }
  return realTarget;
}

function relativePathSegments(value) {
  if (
    typeof value !== 'string'
    || !value
    || value.length > 4_000
    || /[\x00-\x1f\x7f]/.test(value)
    || path.posix.isAbsolute(value)
    || path.win32.isAbsolute(value)
    || /^[A-Za-z]:/.test(value)
  ) {
    throw new Error('The inspected file path is invalid.');
  }
  const segments = value.split(/[\\/]+/);
  if (!segments.length || segments.some((segment) => !segment || segment === '.' || segment === '..')) {
    throw new Error('The inspected file path is invalid.');
  }
  return segments;
}

function isStrictDescendant(root, target) {
  const relative = path.relative(path.resolve(root), path.resolve(target));
  return Boolean(
    relative
    && relative !== '..'
    && !relative.startsWith(`..${path.sep}`)
    && !path.isAbsolute(relative)
  );
}

function boundedDetail(file) {
  const tools = file.tools.length ? file.tools.join(', ') : 'unknown tool';
  const detail = `${file.count} reference(s) via ${tools}`;
  return detail.length <= 500 ? detail : `${detail.slice(0, 497)}...`;
}

module.exports = {
  MAX_INSPECTED_FILE_BYTES,
  MAX_INSPECTED_FILES,
  resolveSessionFilePath,
  sessionFileQuickPickItems,
};
