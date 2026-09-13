// API 客户端：fetch 封装 + 错误归一化（后端错误体 {code,message,detail}）

import type {
  ApiError,
  ChangeEventIn,
  NotificationItem,
  Proposal,
  Trip,
  TripBrief,
  VersionInfo,
} from "./types";

export class HttpError extends Error {
  code: string;
  status: number;
  detail: unknown;

  constructor(status: number, body: ApiError) {
    super(body.message || `HTTP ${status}`);
    this.code = body.code || "HttpError";
    this.status = status;
    this.detail = body.detail;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-User-Id": localStorage.getItem("tc_user") || "u_demo",
    ...(options.headers as Record<string, string>),
  };
  const resp = await fetch(path, { ...options, headers });
  if (!resp.ok) {
    let body: ApiError = { code: "HttpError", message: `HTTP ${resp.status}`, detail: null };
    try {
      body = (await resp.json()).detail as ApiError;
    } catch {
      /* ignore non-JSON error body */
    }
    throw new HttpError(resp.status, body);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export const api = {
  // 行程
  listTrips: () => request<TripBrief[]>("/api/trips"),
  createTrip: (name: string) =>
    request<Trip>("/api/trips", { method: "POST", body: JSON.stringify({ name }) }),
  getTrip: (id: string) => request<Trip>(`/api/trips/${id}`),

  // 提议
  listProposals: (tripId: string, status?: string) =>
    request<Proposal[]>(
      `/api/trips/${tripId}/proposals${status ? `?status=${status}` : ""}`,
    ),
  createProposal: (tripId: string, body: { title: string; reason: string; events: ChangeEventIn[]; emergency?: boolean }) =>
    request<Proposal>(`/api/trips/${tripId}/proposals`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  submitProposal: (tripId: string, pid: string) =>
    request<Proposal>(`/api/trips/${tripId}/proposals/${pid}/submit`, { method: "POST" }),
  adoptProposal: (tripId: string, pid: string, opts: { confirmed?: boolean; force?: boolean; resolution_note?: string } = {}) =>
    request<Proposal>(`/api/trips/${tripId}/proposals/${pid}/adopt`, {
      method: "POST",
      body: JSON.stringify(opts),
    }),
  rejectProposal: (tripId: string, pid: string, reason: string) =>
    request<Proposal>(`/api/trips/${tripId}/proposals/${pid}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  applyEmergency: (tripId: string, pid: string) =>
    request<Proposal>(`/api/trips/${tripId}/proposals/${pid}/emergency`, { method: "POST" }),
  formalizeProposal: (tripId: string, pid: string) =>
    request<Proposal>(`/api/trips/${tripId}/proposals/${pid}/formalize`, { method: "POST" }),
  revokeProposal: (tripId: string, pid: string) =>
    request<Proposal>(`/api/trips/${tripId}/proposals/${pid}/revoke`, { method: "POST" }),

  // 版本 / 回滚 / 通知
  listVersions: (tripId: string) => request<VersionInfo[]>(`/api/trips/${tripId}/versions`),
  rollback: (tripId: string, version: number, reason?: string) =>
    request<{ target_version: number; new_version: number; affected_proposals: string[] }>(
      `/api/trips/${tripId}/rollback`,
      { method: "POST", body: JSON.stringify({ version, reason }) },
    ),
  listNotifications: (tripId: string) =>
    request<NotificationItem[]>(`/api/trips/${tripId}/notifications`),
};
