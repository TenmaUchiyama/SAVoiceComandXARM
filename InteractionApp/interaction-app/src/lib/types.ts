// ─── Common 3D types ───
export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

export interface BoundingBox {
  min: Vec3;
  max: Vec3;
}

export interface UserPose {
  position: Vec3;
  forward: Vec3;
  up?: Vec3;
}

export interface RobotPose {
  position: Vec3;
  forward: Vec3;
}

export interface Utterance {
  text: string;
  language?: string; // default "ja"
}

export interface SceneObject {
  id: string;
  label?: string;
  color?: string;
  shape?: string;
  size?: string;
  relative_direction?: string;
  bounding_box?: BoundingBox;
  position: Vec3;
}

// ─── Spatial Pipeline ───
export interface SpatialReferenceRequest {
  type: "spatial_reference_request";
  request_id: string;
  utterance: Utterance;
  user_pose: UserPose;
  objects: SceneObject[];
  table_frame?: object;
  robot_pose?: RobotPose;
}

export interface RefinementRequest {
  type: "refinement_request";
  request_id: string;
  original_request_id: string;
  utterance: Utterance;
  user_pose?: UserPose;
  previous_target?: string;
}

export interface ConfirmationRequest {
  type: "confirmation";
  request_id: string;
  original_request_id?: string;
  confirmed_object_id: string;
  action?: string;
  accepted: boolean;
  rejection_reason?: string;
}

export interface ConfirmationInterpretationRequest {
  type: "confirmation_interpretation_request";
  request_id: string;
  original_request_id?: string;
  utterance: Utterance;
  confirmed_object_id?: string;
  action?: string;
  user_pose?: UserPose;
}

export interface Candidate {
  object_id: string;
  score: number;
  reasoning: string;
}

export interface SpatialReferenceResult {
  type: "spatial_reference_result";
  request_id: string;
  candidates: Candidate[];
  top_candidate_id: string;
  confidence: number;
  selected_object_id?: string;
  target?: {
    object_id: string;
    confidence: number;
    reference_frame: string;
  };
  ranked_candidates?: Candidate[];
  reasoning?: string;
}

export interface RobotCommand {
  type: "robot_command";
  request_id: string;
  action: string;
  target_object_id: string;
  target_position?: Vec3;
  status: "started" | "completed" | "failed";
  message?: string;
}

export interface ServerError {
  type: "error" | "server_error";
  request_id?: string;
  code?: string;
  message: string;
}

// ─── Status WebSocket ───
export interface StatusMessage {
  type: "status";
  active_sessions: number;
  robot_enabled: boolean;
  session_timeout_sec: number;
  last_error?: object;
}

// ─── Unity PCDebug Protocol ───
export interface LegacyPacket {
  eventId: string;
  payload: string; // JSON-stringified
}

export interface CalibrationAction {
  action:
    | "teach"
    | "restore"
    | "record"
    | "robot"
    | "clear"
    | "restore_local"
    | "status";
}

export interface GridPoint {
  x: number;
  y: number;
  z: number;
  [key: string]: unknown;
}

export interface GridConfig {
  filename?: string;
  gridPoints: GridPoint[];
}

export interface RobotMarkerConfig {
  filename?: string;
  markerData: Record<string, unknown>;
}

// ─── REST API ───
export interface CommandRequest {
  session_id?: string;
  utterance: string;
  user?: {
    position: Vec3;
    forward: Vec3;
    fov_deg?: number;
  };
  robot?: {
    position: Vec3;
    forward: Vec3;
  };
  objects?: SceneObject[];
}

export interface CommandResponse {
  status: "ok" | "error";
  target_id?: string;
  decision?: object;
  llm_input?: object;
  computed_features?: object[];
  reason?: string;
  debug?: object;
}

// ─── Log ───
export type LogDirection = "TX" | "RX";
export type LogSource = "unity" | "spatial" | "status" | "http" | "robot";

export interface LogEntry {
  id: number;
  timestamp: Date;
  direction: LogDirection;
  source: LogSource;
  event: string;
  data: unknown;
}

// ─── Language ───
export type AppLanguage = "ja" | "en";

// ─── Tab ───
export type TabId = "unity" | "xarm" | "spatial" | "log" | "grid";

// ─── Spatial Phase ───
export type SpatialPhase =
  | "idle"
  | "processing"
  | "showing_result"
  | "awaiting_confirmation"
  | "executing";

// ─── Robot API responses ───
export interface RobotActionResponse {
  success: boolean;
  message: string;
}

export interface RobotStatusResponse {
  connected: boolean;
  mode: "real" | "mock";
  state?: number | string | null;
  position?: number[] | null;
  error_code?: number;
  grid_cells_loaded?: number;
  manual_mode?: boolean;
}

export interface GridCell {
  key: string;
  col: number;
  row: number;
  pose: number[];
}

export interface GridCellsResponse {
  cells: GridCell[];
  count: number;
}

// ─── Debug log (server-side) ───
export interface DebugLogEntry {
  ts: string;
  level: "info" | "warn" | "error" | "step";
  source: string;
  message: string;
  detail?: unknown;
}

export interface DebugLogsResponse {
  logs: DebugLogEntry[];
}

export type JogAxis = "x" | "-x" | "y" | "-y" | "z" | "-z";
