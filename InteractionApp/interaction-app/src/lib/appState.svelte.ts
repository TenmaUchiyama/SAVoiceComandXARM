import type {
  TabId,
  SpatialPhase,
  SpatialReferenceResult,
  StatusMessage,
  GridConfig,
  RobotMarkerConfig,
  DebugLogEntry,
  RobotStatusResponse,
  AppLanguage,
} from "./types";
import { WsManager } from "./ws.svelte";

// ─── Connection settings (persisted to localStorage) ───
function loadSetting(key: string, fallback: string): string {
  if (typeof localStorage !== "undefined") {
    return localStorage.getItem(key) ?? fallback;
  }
  return fallback;
}

function saveSetting(key: string, value: string) {
  if (typeof localStorage !== "undefined") {
    localStorage.setItem(key, value);
  }
}

// ─── App State (Svelte 5 $state) ───
let _activeTab = $state<TabId>("unity");
let _unityWsUrl = $state(loadSetting("unity_ws_url", "ws://localhost:8765"));
let _serverBaseUrl = $state(
  loadSetting("server_base_url", "http://localhost:8765"),
);
let _language = $state<AppLanguage>(
  loadSetting("app_language", "en") as AppLanguage,
);
let _robotEnabled = $state(false);
let _spatialPhase = $state<SpatialPhase>("idle");
let _lastResult = $state<SpatialReferenceResult | null>(null);
let _lastTargetId = $state("");
let _lastRequestId = $state("");

// Toasts
export interface Toast {
  id: number;
  message: string;
  type: "info" | "success" | "error";
}
let _toasts = $state<Toast[]>([]);
let _nextToastId = 0;

// Saved configs (local)
let _savedGrids = $state<string[]>([]);
let _savedRobots = $state<string[]>([]);

// Debug logs (from server WebSocket)
const MAX_DEBUG_LOGS = 300;
let _debugLogs = $state<DebugLogEntry[]>([]);

// Robot status (from server WebSocket)
let _robotStatus = $state<RobotStatusResponse | null>(null);

export const appState = {
  // Tab
  get activeTab() {
    return _activeTab;
  },
  set activeTab(v: TabId) {
    _activeTab = v;
  },

  // Connection URLs
  get unityWsUrl() {
    return _unityWsUrl;
  },
  set unityWsUrl(v: string) {
    _unityWsUrl = v;
    saveSetting("unity_ws_url", v);
  },

  get serverBaseUrl() {
    return _serverBaseUrl;
  },
  set serverBaseUrl(v: string) {
    _serverBaseUrl = v;
    saveSetting("server_base_url", v);
  },

  // Language
  get language() {
    return _language;
  },
  set language(v: AppLanguage) {
    _language = v;
    saveSetting("app_language", v);
  },

  // Robot
  get robotEnabled() {
    return _robotEnabled;
  },
  set robotEnabled(v: boolean) {
    _robotEnabled = v;
  },

  // Robot status (detailed)
  get robotStatus() {
    return _robotStatus;
  },
  set robotStatus(v: RobotStatusResponse | null) {
    _robotStatus = v;
  },

  // Spatial
  get spatialPhase() {
    return _spatialPhase;
  },
  set spatialPhase(v: SpatialPhase) {
    _spatialPhase = v;
  },

  get lastResult() {
    return _lastResult;
  },
  set lastResult(v: SpatialReferenceResult | null) {
    _lastResult = v;
  },

  get lastTargetId() {
    return _lastTargetId;
  },
  set lastTargetId(v: string) {
    _lastTargetId = v;
  },

  get lastRequestId() {
    return _lastRequestId;
  },
  set lastRequestId(v: string) {
    _lastRequestId = v;
  },

  // Toasts
  get toasts() {
    return _toasts;
  },

  addToast(message: string, type: Toast["type"] = "info") {
    const id = _nextToastId++;
    _toasts = [..._toasts, { id, message, type }];
    setTimeout(() => {
      _toasts = _toasts.filter((t) => t.id !== id);
    }, 4000);
  },

  // Saved configs
  get savedGrids() {
    return _savedGrids;
  },
  set savedGrids(v: string[]) {
    _savedGrids = v;
  },

  get savedRobots() {
    return _savedRobots;
  },
  set savedRobots(v: string[]) {
    _savedRobots = v;
  },

  // Debug logs
  get debugLogs() {
    return _debugLogs;
  },
  pushDebugLog(entry: DebugLogEntry) {
    _debugLogs = [entry, ..._debugLogs].slice(0, MAX_DEBUG_LOGS);
  },
  clearDebugLogs() {
    _debugLogs = [];
  },
};

// ─── WebSocket instances ───
export const wsUnity = new WsManager({
  url: _unityWsUrl,
  name: "unity",
  autoReconnect: true,
});

export const wsSpatial = new WsManager({
  url: `${_serverBaseUrl.replace("http", "ws")}/spatial`,
  name: "spatial",
  autoReconnect: true,
});

export const wsStatus = new WsManager({
  url: `${_serverBaseUrl.replace("http", "ws")}/status`,
  name: "status",
  autoReconnect: true,
});

export const wsRobot = new WsManager({
  url: `${_serverBaseUrl.replace("http", "ws")}/robot`,
  name: "robot",
  autoReconnect: true,
});

// ─── Status listener ───
wsStatus.on("status", (data) => {
  const msg = data as StatusMessage;
  appState.robotEnabled = msg.robot_enabled;
});

// ─── Status update (robot status via WS) ───
wsStatus.on("status_update", (data) => {
  const d = data as Record<string, unknown>;
  if (typeof d.connected === "boolean") {
    appState.robotStatus = d as unknown as RobotStatusResponse;
  }
});

// ─── Debug log from server ───
wsStatus.on("debug_log", (data) => {
  const d = data as Record<string, unknown>;
  appState.pushDebugLog({
    ts: (d.ts as string) ?? new Date().toISOString(),
    level: (d.level as DebugLogEntry["level"]) ?? "info",
    source: (d.source as string) ?? "server",
    message: (d.message as string) ?? "",
    detail: d.detail,
  });
});
