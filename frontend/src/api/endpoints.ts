// Funções de acesso a cada endpoint da API. Os componentes nunca chamam fetch diretamente.

import { api, type QueryParams } from "./client";
import type {
  Category,
  Comment,
  DashboardSummary,
  HistoryEntry,
  Paginated,
  Priority,
  Ticket,
  TicketStatus,
  User,
  UserSummary,
} from "./types";

const V1 = "/api/v1";

export const authApi = {
  login: (email: string, password: string) =>
    api<{ access: string }>(`${V1}/auth/session/login/`, {
      method: "POST",
      body: { email, password },
      retryOn401: false,
    }),
  logout: () => api<void>(`${V1}/auth/session/logout/`, { method: "POST", retryOn401: false }),
  me: () => api<User>(`${V1}/auth/me/`),
};

export interface TicketFilters extends QueryParams {
  search?: string;
  status?: TicketStatus[];
  priority?: Priority[];
  category?: number;
  assignee?: number;
  requester?: number;
  unassigned?: boolean;
  ordering?: string;
  page?: number;
  page_size?: number;
}

export interface TicketInput {
  title: string;
  description: string;
  category: number;
  priority: Priority;
}

export const ticketsApi = {
  list: (filters: TicketFilters) => api<Paginated<Ticket>>(`${V1}/tickets/`, { params: filters }),
  get: (id: number) => api<Ticket>(`${V1}/tickets/${id}/`),
  create: (data: TicketInput) => api<Ticket>(`${V1}/tickets/`, { method: "POST", body: data }),
  update: (id: number, data: Partial<TicketInput>) =>
    api<Ticket>(`${V1}/tickets/${id}/`, { method: "PATCH", body: data }),
  assign: (id: number, assigneeId: number) =>
    api<Ticket>(`${V1}/tickets/${id}/assign/`, {
      method: "POST",
      body: { assignee_id: assigneeId },
    }),
  changeStatus: (id: number, status: TicketStatus) =>
    api<Ticket>(`${V1}/tickets/${id}/status/`, { method: "POST", body: { status } }),
  comments: (id: number) => api<Comment[]>(`${V1}/tickets/${id}/comments/`),
  addComment: (id: number, body: string, isInternal: boolean) =>
    api<Comment>(`${V1}/tickets/${id}/comments/`, {
      method: "POST",
      body: { body, is_internal: isInternal },
    }),
  history: (id: number) => api<HistoryEntry[]>(`${V1}/tickets/${id}/history/`),
};

export const categoriesApi = {
  list: () => api<Category[]>(`${V1}/categories/`),
};

export const usersApi = {
  technicians: () => api<UserSummary[]>(`${V1}/users/technicians/`),
};

export const dashboardApi = {
  summary: () => api<DashboardSummary>(`${V1}/dashboard/summary/`),
};
