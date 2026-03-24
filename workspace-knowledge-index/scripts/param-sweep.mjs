#!/usr/bin/env node
/**
 * Parameter sweep for WKI search pipeline micro-tuning.
 * Tests one parameter at a time with small variations.
 * Reads current source, patches value, builds, evals, restores.
 */
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const projectRoot = path.resolve(import.meta.dirname, '..', '..');
const wkiRoot = path.resolve(import.meta.dirname, '..');

function build() {
  execSync('npx tsc', { cwd: wkiRoot, stdio: 'ignore' });
}

function evalNdcg() {
  const out = execSync(
    `node workspace-knowledge-index/dist/index.js eval workspace-knowledge-index/eval/gold-set-v2.json`,
    { cwd: projectRoot, encoding: 'utf8', timeout: 120000 },
  );
  const meanMatch = out.match(/Mean:\s+([\d.]+)/);
  const minMatch = out.match(/Min:\s+([\d.]+)/);
  // Extract per-query scores
  const queryScores = [];
  const queryLines = out.split('\n').filter(l => l.match(/^\s+\d+\./));
  for (const line of queryLines) {
    const m = line.match(/\[([\d.]+)\]/);
    if (m) queryScores.push(parseFloat(m[1]));
  }
  return {
    mean: meanMatch ? parseFloat(meanMatch[1]) : 0,
    min: minMatch ? parseFloat(minMatch[1]) : 0,
    queries: queryScores,
  };
}

function patchFile(filePath, oldStr, newStr) {
  const content = fs.readFileSync(filePath, 'utf8');
  if (!content.includes(oldStr)) {
    throw new Error(`Pattern not found in ${filePath}: ${oldStr.slice(0, 50)}`);
  }
  fs.writeFileSync(filePath, content.replace(oldStr, newStr), 'utf8');
}

function restoreFile(filePath, newStr, oldStr) {
  patchFile(filePath, newStr, oldStr);
}

// Define parameter experiments
const searchServicePath = path.join(wkiRoot, 'src/search/search-service.ts');
const crossEncoderPath = path.join(wkiRoot, 'src/search/cross-encoder-reranker.ts');

const experiments = [
  // Cross-encoder blend ratio
  { name: 'CE blend 50:50', file: crossEncoderPath,
    old: 'score: result.score * 0.4 + ((ceScore - minCe) / ceRange) * 0.6',
    new: 'score: result.score * 0.5 + ((ceScore - minCe) / ceRange) * 0.5' },
  { name: 'CE blend 35:65', file: crossEncoderPath,
    old: 'score: result.score * 0.4 + ((ceScore - minCe) / ceRange) * 0.6',
    new: 'score: result.score * 0.35 + ((ceScore - minCe) / ceRange) * 0.65' },
  { name: 'CE blend 45:55', file: crossEncoderPath,
    old: 'score: result.score * 0.4 + ((ceScore - minCe) / ceRange) * 0.6',
    new: 'score: result.score * 0.45 + ((ceScore - minCe) / ceRange) * 0.55' },
  // Rerank weights
  { name: 'Rerank 55/30/15', file: searchServicePath,
    old: 'r.score * (0.60 + overlapRatio * 0.25 + structuralBoost * 0.15 - noisePenalty)',
    new: 'r.score * (0.55 + overlapRatio * 0.30 + structuralBoost * 0.15 - noisePenalty)' },
  { name: 'Rerank 65/20/15', file: searchServicePath,
    old: 'r.score * (0.60 + overlapRatio * 0.25 + structuralBoost * 0.15 - noisePenalty)',
    new: 'r.score * (0.65 + overlapRatio * 0.20 + structuralBoost * 0.15 - noisePenalty)' },
  { name: 'Rerank 60/20/20', file: searchServicePath,
    old: 'r.score * (0.60 + overlapRatio * 0.25 + structuralBoost * 0.15 - noisePenalty)',
    new: 'r.score * (0.60 + overlapRatio * 0.20 + structuralBoost * 0.20 - noisePenalty)' },
  // Candidate limit
  { name: 'CandLimit topK*3', file: searchServicePath,
    old: 'const candidateLimit = Math.max(topK * 5, topK)',
    new: 'const candidateLimit = Math.max(topK * 3, topK)' },
  { name: 'CandLimit topK*7', file: searchServicePath,
    old: 'const candidateLimit = Math.max(topK * 5, topK)',
    new: 'const candidateLimit = Math.max(topK * 7, topK)' },
  // Noise penalty
  { name: 'Noise 0.2', file: searchServicePath,
    old: "const noisePenalty = isNoisePath(filePath) ? 0.3 : 0",
    new: "const noisePenalty = isNoisePath(filePath) ? 0.2 : 0" },
  { name: 'Noise 0.4', file: searchServicePath,
    old: "const noisePenalty = isNoisePath(filePath) ? 0.3 : 0",
    new: "const noisePenalty = isNoisePath(filePath) ? 0.4 : 0" },
];

console.log('=== Parameter Sweep ===\n');
console.log('Baseline eval...');
build();
const baseline = evalNdcg();
console.log(`Baseline: Mean=${baseline.mean.toFixed(3)}, Min=${baseline.min.toFixed(3)}\n`);

const results = [];
for (const exp of experiments) {
  process.stdout.write(`Testing: ${exp.name}... `);
  try {
    patchFile(exp.file, exp.old, exp.new);
    build();
    const result = evalNdcg();
    const delta = result.mean - baseline.mean;
    const symbol = delta > 0.001 ? '↑' : delta < -0.001 ? '↓' : '=';
    console.log(`Mean=${result.mean.toFixed(3)} (${delta >= 0 ? '+' : ''}${delta.toFixed(3)} ${symbol}), Min=${result.min.toFixed(3)}`);
    results.push({ name: exp.name, mean: result.mean, min: result.min, delta, queries: result.queries });
    // Restore
    restoreFile(exp.file, exp.new, exp.old);
  } catch (err) {
    console.log(`ERROR: ${err.message}`);
    // Try to restore
    try { restoreFile(exp.file, exp.new, exp.old); } catch {}
  }
}

// Rebuild original
build();

console.log('\n=== Results (sorted by mean nDCG) ===\n');
const sorted = [...results].sort((a, b) => b.mean - a.mean);
console.log(`${'Name'.padEnd(25)} ${'Mean'.padStart(6)} ${'Delta'.padStart(7)} ${'Min'.padStart(6)}`);
console.log('-'.repeat(50));
console.log(`${'BASELINE'.padEnd(25)} ${baseline.mean.toFixed(3).padStart(6)} ${'+0.000'.padStart(7)} ${baseline.min.toFixed(3).padStart(6)}`);
for (const r of sorted) {
  const d = r.delta >= 0 ? `+${r.delta.toFixed(3)}` : r.delta.toFixed(3);
  console.log(`${r.name.padEnd(25)} ${r.mean.toFixed(3).padStart(6)} ${d.padStart(7)} ${r.min.toFixed(3).padStart(6)}`);
}
