import { api } from "./client";
import type { GateDecisionIn, Run, RunListOut } from "../types";

export async function createRun(userRequest: string): Promise<Run> {
  return api.post<Run>("/api/runs", { user_request: userRequest });
}

export async function listRuns(): Promise<RunListOut> {
  return api.get<RunListOut>("/api/runs");
}

export async function getRun(id: string): Promise<Run> {
  return api.get<Run>(`/api/runs/${id}`);
}

export async function submitDecision(
  runId: string,
  gateId: string,
  payload: GateDecisionIn,
): Promise<void> {
  return api.post(`/api/runs/${runId}/gates/${gateId}/decision`, payload);
}