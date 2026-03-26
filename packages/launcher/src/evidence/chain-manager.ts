/**
 * Hash-chained evidence manager.
 * Persists a per-workspace chain file and verifies the stored linkage before
 * appending new entries.
 */

import * as fs from 'node:fs';
import * as path from 'node:path';

import { sha256, sha256WithSalt } from '../common/fs-helpers.js';

export interface ChainEntry {
  index: number;
  prev_hash: string;
  hash: string;
  timestamp: string;
  spec_sha256: string;
  worker_results_hash: string;
  integrity?: string;
}

export interface ChainFile {
  entries: ChainEntry[];
}

export const GENESIS_HASH = '0'.repeat(64);

export const DEFAULT_CHAIN_FILENAME = 'chain.json';

const SHA256_HEX_PATTERN = /^[a-f0-9]{64}$/;

/**
 * Load a chain file from disk.
 * Returns an empty chain when the file does not exist.
 */
export function loadChain(chainPath: string): ChainFile {
  if (!fs.existsSync(chainPath)) {
    return { entries: [] };
  }

  const raw = fs.readFileSync(chainPath, 'utf8');
  const parsed = JSON.parse(raw) as unknown;

  if (
    typeof parsed !== 'object' ||
    parsed === null ||
    !('entries' in parsed) ||
    !Array.isArray((parsed as { entries?: unknown }).entries)
  ) {
    throw new Error(`Invalid chain file structure: ${chainPath}`);
  }

  return {
    entries: ((parsed as { entries: unknown[] }).entries).map((entry) => {
      if (typeof entry !== 'object' || entry === null) {
        throw new Error(`Invalid chain entry in ${chainPath}`);
      }
      const chainEntry = entry as Partial<ChainEntry>;
      if (
        typeof chainEntry.index !== 'number' ||
        typeof chainEntry.prev_hash !== 'string' ||
        typeof chainEntry.hash !== 'string' ||
        typeof chainEntry.timestamp !== 'string' ||
        typeof chainEntry.spec_sha256 !== 'string' ||
        typeof chainEntry.worker_results_hash !== 'string'
      ) {
        throw new Error(`Invalid chain entry fields in ${chainPath}`);
      }
      return {
        index: chainEntry.index,
        prev_hash: chainEntry.prev_hash,
        hash: chainEntry.hash,
        timestamp: chainEntry.timestamp,
        spec_sha256: chainEntry.spec_sha256,
        worker_results_hash: chainEntry.worker_results_hash,
        integrity: typeof chainEntry.integrity === 'string'
          ? chainEntry.integrity
          : undefined,
      };
    }),
  };
}

/**
 * Compute the salted run hash for a single orchestration result set.
 */
export function computeRunHash(
  specSha256: string,
  workerResultsHash: string,
  salt: string,
): string {
  return sha256WithSalt(specSha256 + workerResultsHash, salt);
}

/**
 * Compute a stable worker-results hash after sorting by worker name.
 */
export function computeWorkerResultsHash(
  results: Array<{ name: string; succeeded: boolean; result_summary?: string }>,
): string {
  const normalized = [...results]
    .sort((left, right) => left.name.localeCompare(right.name))
    .map((result) => ({
      name: result.name,
      succeeded: result.succeeded,
      result_summary: result.result_summary ?? null,
    }));

  return sha256(JSON.stringify(normalized));
}

/**
 * Verify the full chain file for index order, linkage, and stored integrity.
 * The salted run hash itself is reproduced from the manifest salt, not the
 * chain file, so chain verification checks structural integrity on disk.
 */
export function verifyChain(
  chainPath: string,
): { valid: boolean; brokenAt?: number } {
  let chain: ChainFile;
  try {
    chain = loadChain(chainPath);
  } catch {
    return { valid: false, brokenAt: 0 };
  }

  for (let index = 0; index < chain.entries.length; index++) {
    const entry = chain.entries[index];
    const expectedPrevHash = index === 0
      ? GENESIS_HASH
      : chain.entries[index - 1].hash;
    if (!isValidEntry(entry, index, expectedPrevHash)) {
      return { valid: false, brokenAt: index };
    }
  }

  return { valid: true };
}

/**
 * Append a new entry after verifying the current chain state.
 * When the existing chain is malformed or broken, it is preserved as a
 * timestamped `.broken` file and a new genesis chain is started.
 */
export function appendEntry(
  chainPath: string,
  specSha256: string,
  workerResultsHash: string,
  salt: string,
): ChainEntry {
  let chain = safelyLoadAppendableChain(chainPath);

  const verification = verifyChain(chainPath);
  if (!verification.valid) {
    preserveBrokenChain(chainPath);
    chain = { entries: [] };
  }

  const prev = chain.entries.at(-1);
  const prevHash = prev?.hash ?? GENESIS_HASH;
  const entry: ChainEntry = {
    index: chain.entries.length,
    prev_hash: prevHash,
    hash: computeRunHash(specSha256, workerResultsHash, salt),
    timestamp: new Date().toISOString(),
    spec_sha256: specSha256,
    worker_results_hash: workerResultsHash,
  };
  entry.integrity = computeEntryIntegrity(entry);

  const nextChain: ChainFile = {
    entries: [...chain.entries, entry],
  };

  fs.mkdirSync(path.dirname(chainPath), { recursive: true });
  fs.writeFileSync(chainPath, JSON.stringify(nextChain, null, 2), 'utf8');
  return entry;
}

function safelyLoadAppendableChain(chainPath: string): ChainFile {
  try {
    return loadChain(chainPath);
  } catch {
    preserveBrokenChain(chainPath);
    return { entries: [] };
  }
}

function preserveBrokenChain(chainPath: string): void {
  if (!fs.existsSync(chainPath)) {
    return;
  }

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const brokenPath = `${chainPath}.broken.${timestamp}`;
  fs.mkdirSync(path.dirname(brokenPath), { recursive: true });
  fs.renameSync(chainPath, brokenPath);
}

function isValidEntry(
  entry: ChainEntry,
  expectedIndex: number,
  expectedPrevHash: string,
): boolean {
  if (
    entry.index !== expectedIndex ||
    entry.prev_hash !== expectedPrevHash ||
    !SHA256_HEX_PATTERN.test(entry.hash) ||
    !SHA256_HEX_PATTERN.test(entry.spec_sha256) ||
    !SHA256_HEX_PATTERN.test(entry.worker_results_hash)
  ) {
    return false;
  }

  if (entry.integrity === undefined) {
    return true;
  }

  return entry.integrity === computeEntryIntegrity(entry);
}

function computeEntryIntegrity(entry: ChainEntry): string {
  return sha256(
    JSON.stringify({
      index: entry.index,
      prev_hash: entry.prev_hash,
      hash: entry.hash,
      timestamp: entry.timestamp,
      spec_sha256: entry.spec_sha256,
      worker_results_hash: entry.worker_results_hash,
    }),
  );
}
