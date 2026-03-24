#!/usr/bin/env node
/**
 * Model comparison script for WKI embedding model selection.
 *
 * Tests a model by:
 * 1. Updating wki.config.json with the target model
 * 2. Running rebuild
 * 3. Running eval against gold-set-v2.json
 * 4. Reporting nDCG results
 *
 * Usage: node scripts/model-compare.mjs <model-name> <dimensions>
 * Example: node scripts/model-compare.mjs "Xenova/bge-m3" 1024
 */

import { execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const args = process.argv.slice(2);
if (args.length < 2) {
  console.log('Usage: node scripts/model-compare.mjs <model-name> <dimensions> [dtype]');
  console.log('Example: node scripts/model-compare.mjs "Xenova/bge-m3" 1024 q8');
  process.exit(1);
}

const modelName = args[0];
const dimensions = parseInt(args[1], 10);
const dtype = args[2] || 'fp32';
const projectRoot = path.resolve(import.meta.dirname, '..', '..');
const configPath = path.join(projectRoot, 'wki.config.json');
const goldSetPath = 'workspace-knowledge-index/eval/gold-set-v2.json';

console.log(`\n${'='.repeat(60)}`);
console.log(`  Model Comparison: ${modelName} (${dimensions}d, ${dtype})`);
console.log('='.repeat(60));

// 1. Backup and update config
const originalConfig = fs.readFileSync(configPath, 'utf8');
const config = JSON.parse(originalConfig);
const originalModel = config.embedding.local.model;
const originalDims = config.embedding.local.dimensions;
const originalDtype = config.embedding.local.dtype;

config.embedding.local.model = modelName;
config.embedding.local.dimensions = dimensions;
config.embedding.local.dtype = dtype;
fs.writeFileSync(configPath, JSON.stringify(config, null, 2), 'utf8');

console.log(`\n  Config updated: ${originalModel} (${originalDims}d) → ${modelName} (${dimensions}d)`);

try {
  // 2. Rebuild
  console.log('\n  Rebuilding index...');
  const startMs = Date.now();
  const rebuildOutput = execSync(
    `node workspace-knowledge-index/dist/index.js rebuild`,
    { cwd: projectRoot, encoding: 'utf8', timeout: 3600000 },
  );
  const rebuildMs = Date.now() - startMs;

  // Extract file/chunk counts
  const indexedMatch = rebuildOutput.match(/Indexed: (\d+) files, (\d+) chunks/);
  const files = indexedMatch ? indexedMatch[1] : '?';
  const chunks = indexedMatch ? indexedMatch[2] : '?';
  console.log(`  Rebuild: ${files} files, ${chunks} chunks (${(rebuildMs / 1000).toFixed(1)}s)`);

  // 3. Eval
  console.log('\n  Running eval...');
  const evalOutput = execSync(
    `node workspace-knowledge-index/dist/index.js eval ${goldSetPath}`,
    { cwd: projectRoot, encoding: 'utf8', timeout: 120000 },
  );

  // Parse eval output
  const meanMatch = evalOutput.match(/Mean:\s+([\d.]+)/);
  const medianMatch = evalOutput.match(/Median:\s+([\d.]+)/);
  const minMatch = evalOutput.match(/Min:\s+([\d.]+)/);
  const maxMatch = evalOutput.match(/Max:\s+([\d.]+)/);

  console.log('\n  Results:');
  console.log(`  Mean nDCG:   ${meanMatch?.[1] ?? 'N/A'}`);
  console.log(`  Median nDCG: ${medianMatch?.[1] ?? 'N/A'}`);
  console.log(`  Min nDCG:    ${minMatch?.[1] ?? 'N/A'}`);
  console.log(`  Max nDCG:    ${maxMatch?.[1] ?? 'N/A'}`);
  console.log(`  Rebuild:     ${(rebuildMs / 1000).toFixed(1)}s`);

  // Print per-query results
  const queryLines = evalOutput.split('\n').filter(l => l.match(/^\s+\d+\./));
  if (queryLines.length > 0) {
    console.log('\n  Per-query:');
    queryLines.forEach(l => console.log(`  ${l.trim()}`));
  }

  // Check index size
  const lanceDir = path.join(projectRoot, '.knowledge/my-project/vectors.lance');
  try {
    const stat = fs.statSync(lanceDir);
    if (stat.isDirectory()) {
      let totalSize = 0;
      const walk = (dir) => {
        for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
          const p = path.join(dir, entry.name);
          if (entry.isFile()) totalSize += fs.statSync(p).size;
          else if (entry.isDirectory()) walk(p);
        }
      };
      walk(lanceDir);
      console.log(`\n  Vector index size: ${(totalSize / 1024 / 1024).toFixed(1)} MB`);
    }
  } catch { /* */ }

} catch (err) {
  console.error('\n  ERROR:', err.message);
} finally {
  // 4. Restore original config
  config.embedding.local.model = originalModel;
  config.embedding.local.dimensions = originalDims;
  if (originalDtype !== undefined) {
    config.embedding.local.dtype = originalDtype;
  } else {
    delete config.embedding.local.dtype;
  }
  fs.writeFileSync(configPath, JSON.stringify(config, null, 2), 'utf8');
  console.log(`\n  Config restored: ${originalModel} (${originalDims}d)`);
}

console.log('\n' + '='.repeat(60) + '\n');
