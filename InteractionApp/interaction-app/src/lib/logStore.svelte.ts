import type { LogDirection, LogSource, LogEntry } from "./types";

let nextLogId = 1;
const MAX_LOGS = 2000;

// — Svelte 5 reactive log store —
let _logs = $state<LogEntry[]>([]);

export const logStore = {
  get logs() {
    return _logs;
  },

  add(
    direction: LogDirection,
    source: LogSource,
    event: string,
    data: unknown,
  ) {
    const entry: LogEntry = {
      id: nextLogId++,
      timestamp: new Date(),
      direction,
      source,
      event,
      data,
    };
    _logs = [entry, ..._logs].slice(0, MAX_LOGS);
  },

  clear() {
    _logs = [];
  },

  filtered(
    directionFilter: LogDirection | "ALL",
    sourceFilter: LogSource | "ALL",
    eventFilter: string,
  ): LogEntry[] {
    return _logs.filter((e) => {
      if (directionFilter !== "ALL" && e.direction !== directionFilter)
        return false;
      if (sourceFilter !== "ALL" && e.source !== sourceFilter) return false;
      if (
        eventFilter &&
        !e.event.toLowerCase().includes(eventFilter.toLowerCase())
      )
        return false;
      return true;
    });
  },

  exportJsonLines(): string {
    return _logs
      .slice()
      .reverse()
      .map((e) =>
        JSON.stringify({
          id: e.id,
          timestamp: e.timestamp.toISOString(),
          direction: e.direction,
          source: e.source,
          event: e.event,
          data: e.data,
        }),
      )
      .join("\n");
  },
};
