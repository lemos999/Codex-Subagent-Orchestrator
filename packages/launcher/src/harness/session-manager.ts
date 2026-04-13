/**
 * C3: SessionManager — 4-state machine per worker session.
 * created → running → idle | terminated
 */

import type { HarnessEventBus } from './event-bus.js';
import type { SessionState } from './types.js';

const VALID_TRANSITIONS: Record<SessionState, SessionState[]> = {
  created: ['running'],
  running: ['idle', 'terminated'],
  idle: [],
  terminated: [],
};

export class SessionManager {
  private readonly states = new Map<string, SessionState>();
  private readonly bus: HarnessEventBus;

  constructor(bus: HarnessEventBus) {
    this.bus = bus;
  }

  create(sessionId: string): void {
    this.states.set(sessionId, 'created');
    this.bus.emit({
      type: 'session.state_changed',
      sessionId,
      from: 'created',
      to: 'created',
      timestamp: now(),
    });
  }

  transition(sessionId: string, to: SessionState): void {
    const from = this.states.get(sessionId);
    if (!from) return;

    const allowed = VALID_TRANSITIONS[from];
    if (!allowed.includes(to)) return;

    this.states.set(sessionId, to);
    this.bus.emit({
      type: 'session.state_changed',
      sessionId,
      from,
      to,
      timestamp: now(),
    });
  }

  getState(sessionId: string): SessionState | undefined {
    return this.states.get(sessionId);
  }

  getAllSessions(): ReadonlyMap<string, SessionState> {
    return this.states;
  }
}

/**
 * Generate a session ID: {specName}_{workerName}_{YYYYMMDDTHHMMSSmmm}
 */
export function generateSessionId(specName: string, workerName: string): string {
  const safe = (s: string) => s.replace(/[^a-zA-Z0-9_-]/g, '_');
  const d = new Date();
  const ts = [
    d.getFullYear(),
    pad2(d.getMonth() + 1),
    pad2(d.getDate()),
    'T',
    pad2(d.getHours()),
    pad2(d.getMinutes()),
    pad2(d.getSeconds()),
    pad3(d.getMilliseconds()),
  ].join('');

  return `${safe(specName)}_${safe(workerName)}_${ts}`;
}

function pad2(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

function pad3(n: number): string {
  if (n < 10) return `00${n}`;
  if (n < 100) return `0${n}`;
  return String(n);
}

function now(): string {
  return new Date().toISOString();
}
