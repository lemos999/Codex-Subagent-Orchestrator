/**
 * Delegation Framework Smoke Tests
 *
 * Verifies that all 6 core modules of the Intelligent Delegation framework
 * load and function correctly: C1 CapabilityRegistry, C2 Authority,
 * C4 HashChain, C5 TrustRegistry, C6 RiskMatrix, and fs-helpers.
 */

import assert from 'node:assert/strict';
import { describe, test, before, after } from 'node:test';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as os from 'node:os';
import { fileURLToPath } from 'node:url';

// ============================================================
// Imports from dist
// ============================================================

import { CapabilityRegistry } from '../dist/workers/capability-registry.js';
import {
  attenuateAuthority,
  validateAuthority,
  getMaxAuthorityForRisk,
} from '../dist/supervisor/authority.js';
import {
  computeRunHash,
  appendEntry,
  verifyChain,
  GENESIS_HASH,
} from '../dist/evidence/chain-manager.js';
import {
  assessRisk,
  getDefaultRisk,
  overrideRisk,
  getSecurityGate,
} from '../dist/supervisor/risk-matrix.js';
import { TrustRegistry } from '../dist/workers/trust-registry.js';
import { sha256, sha256WithSalt, generateSalt } from '../dist/common/fs-helpers.js';

// ============================================================
// Helpers
// ============================================================

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CONFIG_DIR = path.resolve(__dirname, '../../../config/capabilities');

/** Create a temp directory that is cleaned up after tests. */
function makeTmpDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

// ============================================================
// C1 — Capability Registry
// ============================================================

describe('C1 Capability Registry', () => {
  /** @type {CapabilityRegistry} */
  let registry;

  before(() => {
    registry = new CapabilityRegistry();
    registry.loadProfiles(CONFIG_DIR);
  });

  test('loads 3 YAML files (claude, codex, gemini) with profiles', () => {
    const profiles = registry.getProfiles();
    const engines = [...new Set(profiles.map((p) => p.engine))];
    // claude.yaml, codex.yaml, gemini.yaml should all be present
    assert.ok(engines.includes('claude'), 'claude profiles loaded');
    assert.ok(engines.includes('gemini'), 'gemini profiles loaded');
    assert.ok(profiles.length >= 5, `Expected at least 5 profiles, got ${profiles.length}`);
  });

  test('matchEngine() returns result with engine, model, score, reasoning', () => {
    const result = registry.matchEngine({
      role: 'implementer',
      requiredDimensions: {
        'code-gen': { minScore: 0.5, weight: 1.0 },
        'tool-access': { minScore: 0.5, weight: 0.8 },
      },
      constraints: [],
    });
    assert.ok(result !== null, 'matchEngine should return a result');
    assert.ok(typeof result.engine === 'string', 'engine is string');
    assert.ok(typeof result.model === 'string', 'model is string');
    assert.ok(typeof result.score === 'number', 'score is number');
    assert.ok(Array.isArray(result.reasoning), 'reasoning is array');
  });

  test('constraints filter: gemini excluded from implementer when file-write-capable required', () => {
    const result = registry.matchEngine({
      role: 'implementer',
      requiredDimensions: {
        'code-gen': { minScore: 0.5, weight: 1.0 },
      },
      constraints: [{ type: 'required_tag', tag: 'file-write-capable' }],
    });
    assert.ok(result !== null, 'should have a match');
    assert.notEqual(result.engine, 'gemini', 'gemini should be eliminated');
    // Verify gemini models appear in eliminated candidates
    const geminiEliminated = result.eliminatedCandidates.filter(
      (c) => c.engine === 'gemini',
    );
    assert.ok(
      geminiEliminated.length > 0,
      'gemini should appear in eliminatedCandidates',
    );
  });
});

// ============================================================
// C2 — Authority Profile
// ============================================================

describe('C2 Authority Profile', () => {
  const executeProfile = {
    authority_level: /** @type {4} */ (4),
    writable_scope: ['/project'],
    redelegation_allowed: true,
    max_depth: 3,
  };

  test('attenuateAuthority(execute, depth=1) returns delete (level 3)', () => {
    const result = attenuateAuthority(executeProfile, 1);
    // execute(1.0) * 0.80^1 = 0.80 >= AUTHORITY_VALUES[3]=0.75 -> level 3 (delete)
    assert.equal(result.authority_level, 3, 'depth=1 should attenuate to delete');
  });

  test('attenuateAuthority(execute, depth=2) returns write (level 2)', () => {
    const result = attenuateAuthority(executeProfile, 2);
    // execute(1.0) * 0.80^2 = 0.64 >= AUTHORITY_VALUES[2]=0.50 -> level 2 (write)
    assert.equal(result.authority_level, 2, 'depth=2 should attenuate to write');
  });

  test('validateAuthority(parent=write, child=execute) returns error violation', () => {
    const parentWrite = {
      authority_level: /** @type {2} */ (2),
      writable_scope: ['/project'],
      redelegation_allowed: true,
      max_depth: 3,
    };
    const childExecute = {
      authority_level: /** @type {4} */ (4),
      writable_scope: ['/project'],
      redelegation_allowed: false,
      max_depth: 2,
    };
    const violations = validateAuthority(parentWrite, childExecute);
    assert.ok(violations.length > 0, 'should have violations');
    const escalation = violations.find((v) => v.rule === 'authority_escalation');
    assert.ok(escalation, 'should detect authority_escalation');
    assert.equal(escalation.severity, 'error');
  });
});

// ============================================================
// C4 — Hash Chain
// ============================================================

describe('C4 Hash-Chain', () => {
  let tmpDir;

  before(() => {
    tmpDir = makeTmpDir('chain-smoke-');
  });

  after(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  test('computeRunHash() same inputs produce same hash', () => {
    const specHash = sha256('test-spec');
    const resultsHash = sha256('test-results');
    const salt = 'fixed-salt-for-test';
    const hash1 = computeRunHash(specHash, resultsHash, salt);
    const hash2 = computeRunHash(specHash, resultsHash, salt);
    assert.equal(hash1, hash2, 'identical inputs must produce identical hashes');
    assert.match(hash1, /^[a-f0-9]{64}$/, 'hash must be 64-char hex');
  });

  test('appendEntry() creates chain.json with genesis entry', () => {
    const chainPath = path.join(tmpDir, 'chain.json');
    const specHash = sha256('spec-content');
    const resultsHash = sha256('results-content');
    const salt = generateSalt();

    const entry = appendEntry(chainPath, specHash, resultsHash, salt);

    assert.ok(fs.existsSync(chainPath), 'chain.json should be created');
    assert.equal(entry.index, 0, 'first entry index should be 0');
    assert.equal(entry.prev_hash, GENESIS_HASH, 'first entry prev_hash should be genesis');
  });

  test('verifyChain() returns valid=true on a correct chain', () => {
    const chainPath = path.join(tmpDir, 'chain.json');
    const result = verifyChain(chainPath);
    assert.equal(result.valid, true, 'chain should be valid');
  });
});

// ============================================================
// C6 — Risk Matrix
// ============================================================

describe('C6 Risk Matrix', () => {
  test("assessRisk('reversible', 'low') returns 'L1'", () => {
    assert.equal(assessRisk('reversible', 'low'), 'L1');
  });

  test("assessRisk('irreversible', 'critical') returns 'L4'", () => {
    assert.equal(assessRisk('irreversible', 'critical'), 'L4');
  });

  test("getDefaultRisk('deploy') returns 'L4'", () => {
    assert.equal(getDefaultRisk('deploy'), 'L4');
  });

  test("overrideRisk('L2', 'L1') returns 'L2' (downward blocked)", () => {
    assert.equal(overrideRisk('L2', 'L1'), 'L2');
  });

  test("getSecurityGate('L4').requireHumanApproval is true", () => {
    const gate = getSecurityGate('L4');
    assert.equal(gate.requireHumanApproval, true);
  });
});

// ============================================================
// C5 — Trust Registry
// ============================================================

describe('C5 Trust Registry', () => {
  let tmpDir;

  before(() => {
    tmpDir = makeTmpDir('trust-smoke-');
  });

  after(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  test('recordRun(success) x3 produces trustScore > 0.5', () => {
    const reg = new TrustRegistry(tmpDir);
    reg.recordRun('test-engine-a', true, 100);
    reg.recordRun('test-engine-a', true, 100);
    reg.recordRun('test-engine-a', true, 100);
    const score = reg.getTrustScore('test-engine-a');
    assert.ok(score > 0.5, `trustScore should be > 0.5, got ${score}`);
  });

  test('recordRun(fail) x3 consecutive puts engine in probation', () => {
    const tmpDir2 = makeTmpDir('trust-smoke2-');
    try {
      const reg = new TrustRegistry(tmpDir2);
      // Start with some successes to have a baseline
      reg.recordRun('test-engine-b', true, 100);
      reg.recordRun('test-engine-b', true, 100);
      reg.recordRun('test-engine-b', true, 100);
      // Then 3 consecutive failures
      reg.recordRun('test-engine-b', false, 100);
      reg.recordRun('test-engine-b', false, 100);
      reg.recordRun('test-engine-b', false, 100);
      const tier = reg.getTrustTier('test-engine-b');
      assert.equal(tier, 'probation', 'should be in probation after 3 consecutive failures');
    } finally {
      fs.rmSync(tmpDir2, { recursive: true, force: true });
    }
  });

  test('getTrustTier() returns a valid tier value', () => {
    const reg = new TrustRegistry(tmpDir);
    const tier = reg.getTrustTier('nonexistent-engine');
    assert.ok(
      ['probation', 'standard', 'trusted'].includes(tier),
      `tier should be valid, got ${tier}`,
    );
  });
});

// ============================================================
// Integration Scenarios
// ============================================================

describe('Integration Scenarios', () => {
  test('deploy task: Risk L4, Authority cap write, requireHumanApproval=true', () => {
    // Step 1: deploy -> Risk L4
    const risk = getDefaultRisk('deploy');
    assert.equal(risk, 'L4');

    // Step 2: L4 -> Authority cap = write (level 2)
    const maxAuth = getMaxAuthorityForRisk('L4');
    assert.equal(maxAuth, 2, 'L4 should cap authority at write (level 2)');

    // Step 3: L4 -> SecurityGate requireHumanApproval=true
    const gate = getSecurityGate('L4');
    assert.equal(gate.requireHumanApproval, true);
    assert.equal(gate.dryRunFirst, true);
  });

  test('file_read task: Risk L1, skipGate=true', () => {
    // Step 1: file_read -> Risk L1
    const risk = getDefaultRisk('file_read');
    assert.equal(risk, 'L1');

    // Step 2: L1 -> SecurityGate skipGate=true
    const gate = getSecurityGate('L1');
    assert.equal(gate.skipGate, true);
    assert.equal(gate.requireHumanApproval, false);
  });
});
