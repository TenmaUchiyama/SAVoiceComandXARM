import type {
  CommandRequest,
  CommandResponse,
  RobotStatusResponse,
  RobotActionResponse,
  GridCellsResponse,
  DebugLogsResponse,
} from "./types";
import { logStore } from "./logStore.svelte";

let _serverBaseUrl = $state("http://localhost:8765");

export const apiConfig = {
  get serverBaseUrl() {
    return _serverBaseUrl;
  },
  set serverBaseUrl(v: string) {
    _serverBaseUrl = v;
  },
};

async function post<T>(path: string, body: unknown): Promise<T> {
  const url = `${_serverBaseUrl}${path}`;
  logStore.add("TX", "http", `POST ${path}`, body);

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await res.json();
  logStore.add("RX", "http", `POST ${path} → ${res.status}`, data);

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${JSON.stringify(data)}`);
  }
  return data as T;
}

async function get<T>(path: string): Promise<T> {
  const url = `${_serverBaseUrl}${path}`;
  logStore.add("TX", "http", `GET ${path}`, null);

  const res = await fetch(url);
  const data = await res.json();
  logStore.add("RX", "http", `GET ${path} → ${res.status}`, data);

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${JSON.stringify(data)}`);
  }
  return data as T;
}

export const api = {
  // — Spatial Pipeline (legacy HTTP) —
  postCommand(body: CommandRequest): Promise<CommandResponse> {
    return post("/command", body);
  },

  postCommandCord(body: CommandRequest): Promise<CommandResponse> {
    return post("/command_cord", body);
  },

  saveGridConfig(
    payload: object,
  ): Promise<{ status: string; filename: string }> {
    return post("/save_grid_config", payload);
  },

  // — Robot control —
  robotHome(): Promise<RobotActionResponse> {
    return post("/api/robot/home", {});
  },

  robotInitial(): Promise<RobotActionResponse> {
    return post("/api/robot/initial", {});
  },

  robotReset(): Promise<RobotActionResponse> {
    return post("/api/robot/reset", {});
  },

  robotConnect(): Promise<RobotActionResponse> {
    return post("/api/robot/connect", {});
  },

  robotDisconnect(): Promise<RobotActionResponse> {
    return post("/api/robot/disconnect", {});
  },

  robotGripper(action: "open" | "close"): Promise<RobotActionResponse> {
    return post("/api/robot/gripper", { action });
  },

  robotPick(x: number, y: number): Promise<RobotActionResponse> {
    return post("/api/robot/pick", { x, y });
  },

  robotJog(
    axis: "x" | "-x" | "y" | "-y" | "z" | "-z",
    distance: number = 10,
  ): Promise<RobotActionResponse> {
    return post("/api/robot/jog", { axis, distance });
  },

  robotStatus(): Promise<RobotStatusResponse> {
    return get("/api/robot/status");
  },

  robotManualMode(enabled: boolean): Promise<RobotActionResponse> {
    return post("/api/robot/manual_mode", { enabled });
  },

  // — Robot grid cells (4x4) —
  robotGridCells(): Promise<GridCellsResponse> {
    return get("/api/robot/grid");
  },

  robotGridMove(col: number, row: number): Promise<RobotActionResponse> {
    return post("/api/robot/grid/move", { col, row });
  },

  robotGridReload(): Promise<RobotActionResponse> {
    return post("/api/robot/grid/reload", {});
  },

  // — File API (grid/robot configs) —
  listGrids(): Promise<string[]> {
    return get("/api/files/grids");
  },

  getGrid(name: string): Promise<unknown> {
    return get(`/api/files/grids/${encodeURIComponent(name)}`);
  },

  restoreGrid(name: string): Promise<{ success: boolean; message: string }> {
    return post("/api/files/grids/restore", { filename: name });
  },

  listRobots(): Promise<string[]> {
    return get("/api/files/robots");
  },

  getRobot(name: string): Promise<unknown> {
    return get(`/api/files/robots/${encodeURIComponent(name)}`);
  },

  restoreRobot(name: string): Promise<{ success: boolean; message: string }> {
    return post("/api/files/robots/restore", { filename: name });
  },

  // — Unity commands —
  unityCalib(action: string): Promise<unknown> {
    return post("/unity/calib", { action });
  },

  // — Debug logs —
  debugLogs(): Promise<DebugLogsResponse> {
    return get("/api/debug/logs");
  },

  debugLogsClear(): Promise<RobotActionResponse> {
    return post("/api/debug/logs/clear", {});
  },
};
