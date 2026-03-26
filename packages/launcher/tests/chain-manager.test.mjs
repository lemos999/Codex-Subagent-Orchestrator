import assert from 'node:assert/strict';
import * as fs from 'node:fs/promises';
import * as os from 'node:os';
import * as path from 'node:path';
import { afterEach, beforeEach, describe, test } from 'node:test';

import {
  GENESIS_HASH,
  appendEntry,
  computeRunHash,
  computeWorkerResultsHash,
  loadChain,
  verifyChain,
} from '../dist/evidence/chain-manager.js';

describe('chain-manager', () => {
  let tempRoot = '';

  beforeEach(async () => {
    tempRoot = await fs.mkdtemp(path.join(os.tmpdir(), 'launcher-chain-'));
  });

  afterEach(async () => {
    if (tempRoot) {
      await fs.rm(tempRoot, { recursive: true, force: true });
    }
  });

  test('sorts worker results by name and appends linked chain entries', async () => {
    const chainPath = path.join(tempRoot, 'chain.json');
    const firstResultsHash = computeWorkerResultsHash([
      { name: 'reviewer', succeeded: true, result_summary: 'accepted' },
      { name: 'implementer', succeeded: true, result_summary: 'patched file' },
    ]);
    const secondResultsHash = computeWorkerResultsHash([
      { name: 'implementer', succeeded: true, result_summary: 'patched file' },
      { name: 'reviewer', succeeded: true, result_summary: 'accepted' },
    ]);

    assert.equal(firstResultsHash, secondResultsHash);

    const firstSpecHash = '1'.repeat(64);
    const secondSpecHash = '2'.repeat(64);
    const firstSalt = 'a'.repeat(32);
    const secondSalt = 'b'.repeat(32);

    const firstEntry = appendEntry(chainPath, firstSpecHash, firstResultsHash, firstSalt);
    const secondEntry = appendEntry(chainPath, secondSpecHash, secondResultsHash, secondSalt);

    assert.equal(firstEntry.index, 0);
    assert.equal(firstEntry.prev_hash, GENESIS_HASH);
    assert.equal(
      firstEntry.hash,
      computeRunHash(firstSpecHash, firstResultsHash, firstSalt),
    );
    assert.ok(firstEntry.integrity);

    assert.equal(secondEntry.index, 1);
    assert.equal(secondEntry.prev_hash, firstEntry.hash);
    assert.equal(
      secondEntry.hash,
      computeRunHash(secondSpecHash, secondResultsHash, secondSalt),
    );

    const chain = loadChain(chainPath);
    assert.equal(chain.entries.length, 2);
    assert.deepEqual(verifyChain(chainPath), { valid: true });
  });

  test('preserves a broken chain file and restarts from genesis', async () => {
    const chainPath = path.join(tempRoot, 'chain.json');
    await fs.writeFile(chainPath, '{not-json', 'utf8');

    assert.deepEqual(verifyChain(chainPath), { valid: false, brokenAt: 0 });

    const entry = appendEntry(
      chainPath,
      '3'.repeat(64),
      '4'.repeat(64),
      'c'.repeat(32),
    );
    const files = await fs.readdir(tempRoot);

    assert.equal(entry.index, 0);
    assert.equal(entry.prev_hash, GENESIS_HASH);
    assert.deepEqual(verifyChain(chainPath), { valid: true });
    assert.ok(files.some((file) => file.startsWith('chain.json.broken.')));
  });
});
