'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const {
  MAX_INSPECTED_FILE_BYTES,
  resolveSessionFilePath,
  sessionFileQuickPickItems,
} = require('../src/sessionInspectorFiles');

test('resolves only available regular files inside the real workspace', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'vibeagent-inspected-files-'));
  const outside = await fs.mkdtemp(path.join(os.tmpdir(), 'vibeagent-outside-file-'));
  try {
    await fs.mkdir(path.join(root, 'src'));
    await fs.writeFile(path.join(root, 'src', 'app.py'), 'print("ok")\n');
    await fs.writeFile(path.join(outside, 'secret.txt'), 'secret\n');
    await fs.symlink(path.join(root, 'src', 'app.py'), path.join(root, 'inside-link.py'));
    await fs.symlink(path.join(outside, 'secret.txt'), path.join(root, 'outside-link.txt'));

    const target = await resolveSessionFilePath(root, 'src/app.py');
    assert.equal(target, await fs.realpath(path.join(root, 'src', 'app.py')));
    assert.equal(
      await resolveSessionFilePath(root, 'inside-link.py'),
      await fs.realpath(path.join(root, 'src', 'app.py')),
    );
    for (const invalid of [
      '', '.', '../secret.txt', 'src/../secret.txt', '/etc/passwd',
      'C:\\secret.txt', 'C:secret.txt', '\\\\server\\share\\secret.txt', 'src\0app.py',
    ]) {
      await assert.rejects(resolveSessionFilePath(root, invalid), /inspected file path|outside the workspace/);
    }
    await assert.rejects(resolveSessionFilePath(root, 'src'), /not a regular file/);
    await assert.rejects(resolveSessionFilePath(root, 'missing.py'));
    await assert.rejects(resolveSessionFilePath(root, 'outside-link.txt'), /resolves outside the workspace/);
  } finally {
    await fs.rm(root, { recursive: true, force: true });
    await fs.rm(outside, { recursive: true, force: true });
  }
});

test('bounds file size and filters unavailable quick-pick entries', async () => {
  const oversizedFileSystem = {
    async realpath(value) { return value; },
    async lstat() {
      return { isFile: () => true, size: MAX_INSPECTED_FILE_BYTES + 1 };
    },
  };
  await assert.rejects(
    resolveSessionFilePath('/workspace', 'large.bin', oversizedFileSystem),
    /exceeds 10485760 bytes/,
  );

  const files = [
    { path: 'src/app.py', uses: ['read', 'write'], tools: ['read_file'], count: 2 },
    { path: '../secret', uses: ['read'], tools: ['read_file'], count: 1 },
  ];
  const items = await sessionFileQuickPickItems('/workspace', files, async (_root, value) => {
    if (value.startsWith('..')) throw new Error('outside');
    return `/workspace/${value}`;
  });
  assert.deepEqual(items, [{
    label: 'src/app.py',
    description: 'read, write',
    detail: '2 reference(s) via read_file',
    sourcePath: 'src/app.py',
    targetPath: '/workspace/src/app.py',
  }]);
  await assert.rejects(
    sessionFileQuickPickItems('/workspace', Array.from({ length: 101 }, () => files[0])),
    /invalid inspected file list/,
  );
});

test('rejects a real-path change during one filesystem validation', async () => {
  let targetReads = 0;
  const racingFileSystem = {
    async realpath(value) {
      if (value === '/workspace') return value;
      targetReads += 1;
      return targetReads === 1 ? '/workspace/app.py' : '/outside/app.py';
    },
    async lstat() { return { isFile: () => true, size: 10 }; },
  };
  await assert.rejects(
    resolveSessionFilePath('/workspace', 'app.py', racingFileSystem),
    /changed during validation/,
  );
});
