// 与后端 OpenAPI 对齐的类型定义

export interface Item {
  id: string;
  day: number;
  position: number;
  title: string;
  refs: string[];
  amount: number | null;
  note: string;
  time: string; // 展示时间，如 "09:30"
  tag: string; // 条目类型：景区/饭店/酒店/交通/购物/其他（空=其他）
}

export interface Member {
  user_id: string;
  role: "owner" | "editor" | "member";
}

export interface Trip {
  id: string;
  name: string;
  created_by: string;
  created_at: string;
  version: number;
  days: Record<number, Item[]>;
  members: Member[];
  pending_count: number;
  notify_count: number;
}

export interface TripBrief {
  id: string;
  name: string;
  created_by: string;
  created_at: string;
  version: number;
  item_count: number;
  pending_count: number;
}

export type ChangeEventKind = "created" | "updated" | "deleted";

export interface ChangeEventIn {
  kind: ChangeEventKind;
  item_id: string;
  payload?: Record<string, unknown> | null;
}

export interface Proposal {
  id: string;
  title: string;
  reason: string;
  created_by: string;
  status: "draft" | "pending" | "adopted" | "rejected" | "revoked";
  emergency: boolean;
  created_at: number | null;
  submitted_at: number | null;
  adopted_at: number | null;
  adopted_version: number | null;
  reject_reason: string | null;
  resolution_note: string | null;
  events: { kind: ChangeEventKind; item_id: string; payload: unknown }[];
  warnings: string[];
  hard_conflicts: string[];
}

export interface VersionInfo {
  version: number;
  kind: "adopt" | "emergency" | "rollback" | "revoke";
  proposal_id: string | null;
  title: string | null;
  adopted_at: number;
  item_count: number;
}

export interface NotificationItem {
  seq: number;
  kind: string;
  actor: string;
  payload: Record<string, unknown>;
}

export interface ApiError {
  code: string;
  message: string;
  detail: unknown;
}
