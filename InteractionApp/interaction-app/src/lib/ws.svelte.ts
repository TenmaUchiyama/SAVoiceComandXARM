import type { LogSource } from "./types";
import { logStore } from "./logStore.svelte";

type EventHandler = (data: unknown) => void;

export interface WsManagerOptions {
  url: string;
  name: LogSource;
  autoReconnect?: boolean;
  reconnectIntervalMs?: number;
}

export class WsManager {
  // Reactive state
  connected = $state(false);
  lastError = $state("");

  private ws: WebSocket | null = null;
  private handlers = new Map<string, Set<EventHandler>>();
  private wildcardHandlers = new Set<EventHandler>();
  private options: Required<WsManagerOptions>;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private manualClose = false;

  constructor(options: WsManagerOptions) {
    this.options = {
      autoReconnect: true,
      reconnectIntervalMs: 3000,
      ...options,
    };
  }

  connect(url?: string) {
    if (url) this.options.url = url;
    this.manualClose = false;
    this.clearReconnect();

    try {
      this.ws = new WebSocket(this.options.url);
    } catch (e) {
      this.lastError = `Failed to create WebSocket: ${e}`;
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.connected = true;
      this.lastError = "";
      logStore.add("RX", this.options.name, "ws_connected", {
        url: this.options.url,
      });
    };

    this.ws.onclose = (ev) => {
      this.connected = false;
      logStore.add("RX", this.options.name, "ws_closed", {
        code: ev.code,
        reason: ev.reason,
      });
      if (!this.manualClose && this.options.autoReconnect) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = (ev) => {
      this.lastError = "WebSocket error";
      logStore.add("RX", this.options.name, "ws_error", {
        message: "WebSocket error",
      });
    };

    this.ws.onmessage = (ev) => {
      let parsed: unknown;
      try {
        parsed = JSON.parse(ev.data);
      } catch {
        parsed = ev.data;
      }

      // Determine event name
      let eventName = "unknown";
      if (typeof parsed === "object" && parsed !== null) {
        const obj = parsed as Record<string, unknown>;
        if (obj.type) {
          eventName = String(obj.type);
        } else if (obj.eventId) {
          eventName = String(obj.eventId);
        }
      }

      logStore.add("RX", this.options.name, eventName, parsed);

      // Dispatch to specific handlers
      const handlers = this.handlers.get(eventName);
      if (handlers) {
        for (const h of handlers) h(parsed);
      }
      // Dispatch to wildcard handlers
      for (const h of this.wildcardHandlers) h(parsed);
    };
  }

  /** Send a raw-format message: { type, request_id, ...fields } */
  send(type: string, payload: Record<string, unknown> = {}) {
    const msg = { type, ...payload };
    this.sendRaw(msg);
    logStore.add("TX", this.options.name, type, msg);
  }

  /** Send a legacy-format message: { eventId, payload: JSON.stringify(...) } */
  sendLegacy(eventId: string, payload: object) {
    const msg = { eventId, payload: JSON.stringify(payload) };
    this.sendRaw(msg);
    logStore.add("TX", this.options.name, eventId, { eventId, payload });
  }

  /** Send arbitrary JSON */
  sendRaw(data: unknown) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.lastError = "WebSocket not connected";
      return;
    }
    this.ws.send(JSON.stringify(data));
  }

  /** Send raw text */
  sendText(text: string) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.lastError = "WebSocket not connected";
      return;
    }
    this.ws.send(text);
    logStore.add("TX", this.options.name, "raw_text", text);
  }

  on(event: string, handler: EventHandler) {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event)!.add(handler);
  }

  off(event: string, handler?: EventHandler) {
    if (handler) {
      this.handlers.get(event)?.delete(handler);
    } else {
      this.handlers.delete(event);
    }
  }

  /** Register a handler for ALL incoming messages */
  onAny(handler: EventHandler) {
    this.wildcardHandlers.add(handler);
  }

  offAny(handler: EventHandler) {
    this.wildcardHandlers.delete(handler);
  }

  close() {
    this.manualClose = true;
    this.clearReconnect();
    this.ws?.close();
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, this.options.reconnectIntervalMs);
  }

  private clearReconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}

// Generate unique request IDs
let _reqCounter = 0;
export function generateRequestId(prefix = "req"): string {
  return `${prefix}_${Date.now()}_${++_reqCounter}`;
}
