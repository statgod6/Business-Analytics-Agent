import { api, getToken } from "./client";
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

export interface FileMeta {
  original_name: string;
  stored_name: string;
  path: string;
  size: number;
  uploaded_at: string;
}

export async function uploadFile(
  runId: string,
  file: File,
  onProgress?: (pct: number) => void,
): Promise<{ files: FileMeta[] }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/api/runs/${runId}/files`);
    const token = getToken();
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        try {
          const err = JSON.parse(xhr.responseText);
          reject(new Error(err.detail || "Upload failed"));
        } catch {
          reject(new Error("Upload failed"));
        }
      }
    };

    xhr.onerror = () => reject(new Error("Network error"));

    const formData = new FormData();
    formData.append("file", file);
    xhr.send(formData);
  });
}