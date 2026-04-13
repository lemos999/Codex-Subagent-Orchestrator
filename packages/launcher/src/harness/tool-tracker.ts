/**
 * C5: ToolTracker — aggregates tool usage per worker from events.
 */

import type { HarnessEventBus } from './event-bus.js';
import type { ToolUsageSummary, WorkerToolUseEvent } from './types.js';

export class ToolTracker {
  private readonly usage = new Map<string, Map<string, number>>();

  constructor(bus: HarnessEventBus) {
    bus.on('worker.tool_use', (event: WorkerToolUseEvent) => {
      this.onToolUse(event);
    });
  }

  private onToolUse(event: WorkerToolUseEvent): void {
    let toolMap = this.usage.get(event.sessionId);
    if (!toolMap) {
      toolMap = new Map();
      this.usage.set(event.sessionId, toolMap);
    }
    toolMap.set(event.tool, (toolMap.get(event.tool) ?? 0) + 1);
  }

  getSummary(sessionId: string): ToolUsageSummary[] {
    const toolMap = this.usage.get(sessionId);
    if (!toolMap) return [];

    return Array.from(toolMap.entries()).map(([name, calls]) => ({ name, calls }));
  }
}
