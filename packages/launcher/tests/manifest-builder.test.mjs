import assert from 'node:assert/strict';
import * as path from 'node:path';
import { describe, test } from 'node:test';

import { buildManifest } from '../dist/evidence/manifest-builder.js';

describe('manifest-builder', () => {
  test('includes C4 evidence when provided', () => {
    const workspaceRoot = path.join('C:', 'workspace');
    const outputDir = path.join(workspaceRoot, 'subagent-runs', 'codex', 'manifest-evidence');

    const manifest = buildManifest(
      {
        agents: [],
        cwd: '.',
      },
      {
        workspaceRoot,
        outputDir,
        manifestFile: path.join(outputDir, 'orchestration-manifest.json'),
        summaryFile: path.join(outputDir, 'orchestration-summary.md'),
        debugLogFile: null,
        archiveRoot: null,
        specPath: path.join(workspaceRoot, 'specs', 'sample.json'),
        specDirectory: path.join(workspaceRoot, 'specs'),
        invocationCwd: workspaceRoot,
      },
      [],
      [],
      { text: null, source: null, sha256: null },
      'f'.repeat(64),
      undefined,
      undefined,
      {
        chain_index: 7,
        prev_hash: '1'.repeat(64),
        current_hash: '2'.repeat(64),
        salt: 'a'.repeat(32),
        spec_sha256: 'f'.repeat(64),
      },
    );

    assert.deepEqual(manifest.evidence, {
      chain_index: 7,
      prev_hash: '1'.repeat(64),
      current_hash: '2'.repeat(64),
      salt: 'a'.repeat(32),
      spec_sha256: 'f'.repeat(64),
    });
  });
});
