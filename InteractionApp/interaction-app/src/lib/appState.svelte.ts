import type {
  TabId,
  SpatialPhase,
  SpatialReferenceResult,
  StatusMessage,
  GridConfig,
  RobotMarkerConfig,
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

  // Robot
  get robotEnabled() {
    return _robotEnabled;
  },
  set robotEnabled(v: boolean) {
    _robotEnabled = v;
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

// ─── Status listener ───
wsStatus.on("status", (data) => {
  const msg = data as StatusMessage;
  appState.robotEnabled = msg.robot_enabled;
});
