// Tipos que espelham as respostas da API Django (ver /api/docs/).

export type Role = "ADMIN" | "TECHNICIAN" | "REQUESTER";

export type TicketStatus =
  | "OPEN"
  | "IN_PROGRESS"
  | "WAITING_REQUESTER"
  | "RESOLVED"
  | "CLOSED"
  | "CANCELLED";

export type Priority = 1 | 2 | 3 | 4;

export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: Role;
  is_active: boolean;
  date_joined: string;
}

export interface UserSummary {
  id: number;
  full_name: string;
  email: string;
}

export interface Category {
  id: number;
  name: string;
  description: string;
  is_active: boolean;
}

/** Ações que o usuário logado pode fazer no chamado. Calculado pelo backend. */
export interface TicketPermissions {
  editable_fields: Array<"title" | "description" | "category" | "priority">;
  status_transitions: TicketStatus[];
  can_assign: boolean;
  can_take: boolean;
  can_comment: boolean;
  can_comment_internal: boolean;
}

export interface Ticket {
  id: number;
  title: string;
  description: string;
  category: number;
  category_name: string;
  priority: Priority;
  status: TicketStatus;
  requester: UserSummary;
  assignee: UserSummary | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  closed_at: string | null;
  permissions: TicketPermissions;
}

export interface Comment {
  id: number;
  author: UserSummary;
  body: string;
  is_internal: boolean;
  created_at: string;
}

export interface HistoryEntry {
  id: number;
  action: "CREATED" | "UPDATED" | "STATUS_CHANGED" | "ASSIGNED";
  action_display: string;
  field: string;
  old_value: string;
  new_value: string;
  actor: UserSummary;
  created_at: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface DashboardSummary {
  total: number;
  open: number;
  unassigned: number;
  assigned_to_me: number;
  resolved_last_30_days: number;
  avg_resolution_hours: number | null;
  by_status: Array<{ status: TicketStatus; label: string; count: number }>;
  by_priority: Array<{ priority: Priority; label: string; count: number }>;
  open_by_category: Array<{ id: number; name: string; count: number }>;
}
