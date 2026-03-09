import type { CommandRequest, CommandResponse } from "./types";
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
  robotHome(): Promise<unknown> {
    return post("/api/robot/home", {});
  },

  robotInitial(): Promise<unknown> {
    return post("/api/robot/initial", {});
  },

  robotReset(): Promise<unknown> {
    return post("/api/robot/reset", {});
  },

  robotGripper(action: "open" | "close"): Promise<unknown> {
    return post("/api/robot/gripper", { action });
  },

  robotPick(x: number, y: number): Promise<unknown> {
    return post("/api/robot/pick", { x, y });
  },

  robotStatus(): Promise<unknown> {
    return get("/api/robot/status");
  },

  // — File API (grid/robot configs) —
  listGrids(): Promise<string[]> {
    return get("/api/files/grids");
  },

  getGrid(name: string): Promise<unknown> {
    return get(`/api/files/grids/${encodeURIComponent(name)}`);
  },

  listRobots(): Promise<string[]> {
    return get("/api/files/robots");
  },

  getRobot(name: string): Promise<unknown> {
    return get(`/api/files/robots/${encodeURIComponent(name)}`);
  },
};
