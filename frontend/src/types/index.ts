/* ── Auth ─────────────────────────────────────────────── */

export interface User {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface UserRegister {
  email: string;
  password: string;
}

export interface TokenOut {
  access_token: string;
  token_type: string;
}

/* ── Runs ─────────────────────────────────────────────── */

export interface Run {
  id: string;
  status: "pending" | "running" | "completed" | "failed";
  current_stage: number | null;
  user_request: string;
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface RunCreate {
  user_request: string;
}

export interface RunListOut {
  runs: Run[];
  total: number;
}

/* ── Gate Decisions ───────────────────────────────────── */

export interface GateDecisionIn {
  action: "approve" | "regenerate" | "send_back" | "edit";
  feedback?: string;
  target_stage?: number | null;
  edit_payload?: Record<string, unknown> | null;
}

export interface GateDecisionOut {
  status: string;
}

/* ── WebSocket Events ─────────────────────────────────── */

export interface WSStageSigned {
  type: "stage_signed";
  stage: number;
  artifact_name: string;
}

export interface WSGateOpen {
  type: "gate_open";
  gate_id: string;
  stage: number;
  artifact: Record<string, unknown> | null;
  question: string;
}

export interface WSGateClosed {
  type: "gate_closed";
  gate_id: string;
  decision: string;
}

export interface WSRunStarted {
  type: "run_started";
  run_id: string;
}

export interface WSRunComplete {
  type: "run_complete";
  run_id: string;
}

export interface WSRunError {
  type: "run_error";
  stage?: number;
  detail: string;
}

export type WSEvent =
  | WSStageSigned
  | WSGateOpen
  | WSGateClosed
  | WSRunStarted
  | WSRunComplete
  | WSRunError;

/* ── Stage names ──────────────────────────────────────── */

export const STAGE_NAMES: Record<number, string> = {
  1: "Problem Definition",
  2: "Data Collection",
  3: "Data Preparation",
  4: "Analysis",
  5: "Interpretation",
  6: "Recommendation",
};

export const STAGE_COLORS: Record<number, string> = {
  1: "text-sky-400",
  2: "text-emerald-400",
  3: "text-amber-400",
  4: "text-rose-400",
  5: "text-violet-400",
  6: "text-emerald-500",
};