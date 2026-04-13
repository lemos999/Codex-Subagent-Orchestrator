/**
 * S2: EventLogWriter — persists events as JSON-L files.
 * One file per worker: {name}.events.jsonl
 */

import * as fs from 'node:fs';
import * as path from 'node:path';
import type { HarnessEventBus } from './event-bus.js';
import type { HarnessEvent } from './types.js';

export class EventLogWriter {
  private readonly outputDir: string;
  private readonly sessionToName = new Map<string, string>();

  constructor(bus: HarnessEventBus, outputDir: string) {
    this.outputDir = outputDir;

    // Map sessionId to worker name from spawned events
    bus.on('worker.spawned', (event) => {
      this.sessionToName.set(event.sessionId, event.name);
    });

    // Write all events that have a sessionId
    const eventTypes: HarnessEvent['type'][] = [
      'worker.spawned', 'worker.chunk', 'worker.tool_use',
      'worker.message', 'worker.completed', 'worker.error',
      'session.state_changed',
    ];

    for (const type of eventTypes) {
      bus.on(type, (event: HarnessEvent) => {
        this.writeEvent(event);
      });
    }

    // Stage events go to a shared log
    bus.on('stage.started', (event) => {
      this.writeStageEvent(event);
    });
    bus.on('stage.completed', (event) => {
      this.writeStageEvent(event);
    });
  }

  private writeEvent(event: HarnessEvent): void {
    const sessionId = 'sessionId' in event ? (event as { sessionId: string }).sessionId : null;
    if (!sessionId) return;

    const name = this.sessionToName.get(sessionId);
    if (!name) return;

    const filePath = path.join(this.outputDir, `${name}.events.jsonl`);
    try {
      fs.appendFileSync(filePath, JSON.stringify(event) + '\n', 'utf8');
    } catch {
      // Ignore write errors during event logging
    }
  }

  private writeStageEvent(event: HarnessEvent): void {
    const filePath = path.join(this.outputDir, 'stages.events.jsonl');
    try {
      fs.appendFileSync(filePath, JSON.stringify(event) + '\n', 'utf8');
    } catch {
      // Ignore write errors
    }
  }
}
