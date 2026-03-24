/**
 * Tracker interface — returns raw issues only.
 * Normalization and fingerprinting happen in issue-normalizer.
 */

import type { RawIssue } from '../queue-types.js';

export interface Tracker {
  fetchRawIssues(): Promise<RawIssue[]>;
}
