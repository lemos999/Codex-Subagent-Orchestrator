import assert from 'node:assert/strict';
import { describe, test } from 'node:test';

import {
  assessRisk,
  getDefaultRisk,
  getSecurityGate,
  overrideRisk,
} from '../dist/supervisor/risk-matrix.js';

describe('risk-matrix', () => {
  test('assesses the two-axis risk matrix', () => {
    assert.equal(assessRisk('reversible', 'low'), 'L1');
    assert.equal(assessRisk('reversible', 'critical'), 'L3');
    assert.equal(assessRisk('irreversible', 'medium'), 'L3');
    assert.equal(assessRisk('irreversible', 'critical'), 'L4');
  });

  test('returns default task risk and only allows upward overrides', () => {
    assert.equal(getDefaultRisk('file_modify'), 'L2');
    assert.equal(getDefaultRisk('git_force_push'), 'L4');
    assert.equal(overrideRisk('L2', 'L4'), 'L4');
    assert.equal(overrideRisk('L3', 'L1'), 'L3');
  });

  test('maps higher risk levels to inherited security gates', () => {
    assert.deepEqual(getSecurityGate('L1'), {
      skipGate: true,
      singleEngineVerify: false,
      crossConsensus: false,
      hashRecord: false,
      dryRunFirst: false,
      requireHumanApproval: false,
    });
    assert.deepEqual(getSecurityGate('L3'), {
      skipGate: false,
      singleEngineVerify: true,
      crossConsensus: true,
      hashRecord: true,
      dryRunFirst: false,
      requireHumanApproval: false,
    });
    assert.deepEqual(getSecurityGate('L4'), {
      skipGate: false,
      singleEngineVerify: true,
      crossConsensus: true,
      hashRecord: true,
      dryRunFirst: true,
      requireHumanApproval: true,
    });
  });
});
