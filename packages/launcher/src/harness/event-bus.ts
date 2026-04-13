/**
 * C1: HarnessEventBus — typed callback-based event bus.
 * Synchronous emit, guaranteed event ordering.
 * Zero external dependencies.
 */

import type { HarnessEvent } from './types.js';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyListener = (event: any) => void;

export class HarnessEventBus {
  private readonly listeners = new Map<string, Set<AnyListener>>();
  private readonly eventCounts = new Map<string, number>();

  /**
   * Subscribe to a specific event type.
   */
  on<T extends HarnessEvent['type']>(
    type: T,
    listener: (event: Extract<HarnessEvent, { type: T }>) => void,
  ): void {
    let set = this.listeners.get(type);
    if (!set) {
      set = new Set();
      this.listeners.set(type, set);
    }
    set.add(listener);
  }

  /**
   * Unsubscribe from a specific event type.
   */
  off<T extends HarnessEvent['type']>(
    type: T,
    listener: (event: Extract<HarnessEvent, { type: T }>) => void,
  ): void {
    const set = this.listeners.get(type);
    if (set) {
      set.delete(listener);
    }
  }

  /**
   * Emit an event synchronously to all registered listeners.
   * Listener errors are caught — the bus never stops.
   */
  emit(event: HarnessEvent): void {
    // Track per-session event count
    const sessionId = 'sessionId' in event ? (event as { sessionId: string }).sessionId : null;
    if (sessionId) {
      this.eventCounts.set(sessionId, (this.eventCounts.get(sessionId) ?? 0) + 1);
    }

    const set = this.listeners.get(event.type);
    if (!set) return;

    for (const listener of set) {
      try {
        listener(event);
      } catch {
        // Listener error — swallow and continue to next listener
      }
    }
  }

  /**
   * Get the number of events emitted for a session.
   * Used by S4 ManifestExtension for `events_emitted` field.
   */
  getEventCount(sessionId: string): number {
    return this.eventCounts.get(sessionId) ?? 0;
  }

  /**
   * Remove all listeners and reset counters.
   */
  clear(): void {
    this.listeners.clear();
    this.eventCounts.clear();
  }
}
