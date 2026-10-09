import type { Priority, Role, TicketStatus } from "../api/types";

// Cores de status e prioridade definidas em UM lugar e usadas em todo o app.

export const STATUS_META: Record<TicketStatus, { label: string; badge: string; dot: string }> = {
  OPEN: { label: "Aberto", badge: "bg-sky-50 text-sky-700 ring-sky-600/20", dot: "bg-sky-500" },
  IN_PROGRESS: {
    label: "Em atendimento",
    badge: "bg-indigo-50 text-indigo-700 ring-indigo-600/20",
    dot: "bg-indigo-500",
  },
  WAITING_REQUESTER: {
    label: "Aguardando solicitante",
    badge: "bg-amber-50 text-amber-800 ring-amber-600/20",
    dot: "bg-amber-500",
  },
  RESOLVED: {
    label: "Resolvido",
    badge: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
    dot: "bg-emerald-500",
  },
  CLOSED: { label: "Fechado", badge: "bg-slate-100 text-slate-700 ring-slate-500/20", dot: "bg-slate-400" },
  CANCELLED: {
    label: "Cancelado",
    badge: "bg-rose-50 text-rose-700 ring-rose-600/20",
    dot: "bg-rose-400",
  },
};

export const STATUS_ORDER: TicketStatus[] = [
  "OPEN",
  "IN_PROGRESS",
  "WAITING_REQUESTER",
  "RESOLVED",
  "CLOSED",
  "CANCELLED",
];

/** Texto do botão de uma transição. O mesmo destino pode ter nomes diferentes conforme a origem. */
export function transitionLabel(from: TicketStatus, to: TicketStatus): string {
  if (to === "IN_PROGRESS") {
    if (from === "RESOLVED") return "Reabrir (não foi resolvido)";
    if (from === "WAITING_REQUESTER") return "Retomar atendimento";
    return "Iniciar atendimento";
  }
  const labels: Partial<Record<TicketStatus, string>> = {
    WAITING_REQUESTER: "Aguardar solicitante",
    RESOLVED: "Marcar como resolvido",
    CLOSED: "Confirmar solução",
    CANCELLED: "Cancelar chamado",
  };
  return labels[to] ?? STATUS_META[to].label;
}

export const PRIORITY_META: Record<Priority, { label: string; badge: string; bar: string }> = {
  1: { label: "Baixa", badge: "text-slate-600", bar: "bg-slate-400" },
  2: { label: "Média", badge: "text-sky-700", bar: "bg-sky-500" },
  3: { label: "Alta", badge: "text-orange-700", bar: "bg-orange-500" },
  4: { label: "Crítica", badge: "text-red-700", bar: "bg-red-600" },
};

export const PRIORITIES: Priority[] = [1, 2, 3, 4];

export const ROLE_LABEL: Record<Role, string> = {
  ADMIN: "Administrador",
  TECHNICIAN: "Técnico",
  REQUESTER: "Solicitante",
};

export const FIELD_LABEL: Record<string, string> = {
  title: "Título",
  description: "Descrição",
  category: "Categoria",
  priority: "Prioridade",
  status: "Status",
  assignee: "Responsável",
};

const dateTime = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });
const relative = new Intl.RelativeTimeFormat("pt-BR", { numeric: "auto" });

export function formatDateTime(iso: string): string {
  return dateTime.format(new Date(iso));
}

/** "há 5 minutos", "ontem"... */
export function formatRelative(iso: string, now = Date.now()): string {
  const seconds = Math.round((new Date(iso).getTime() - now) / 1000);
  const units: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ["year", 31536000],
    ["month", 2592000],
    ["day", 86400],
    ["hour", 3600],
    ["minute", 60],
  ];
  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size) return relative.format(Math.round(seconds / size), unit);
  }
  return "agora mesmo";
}

export function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]!.toUpperCase())
    .join("");
}
