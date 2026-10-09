import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Plus, Search, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { errorMessage } from "../api/client";
import { categoriesApi, ticketsApi, usersApi, type TicketFilters } from "../api/endpoints";
import type { Priority, Ticket, TicketStatus } from "../api/types";
import { useCurrentUser } from "../auth/AuthContext";
import {
  Avatar,
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  PriorityBadge,
  StatusBadge,
  inputClass,
} from "../components/ui";
import { PRIORITIES, PRIORITY_META, STATUS_META, STATUS_ORDER, formatRelative } from "../lib/labels";
import { useDebounce } from "../lib/useDebounce";

const PAGE_SIZE = 20;
const ACTIVE: TicketStatus[] = ["OPEN", "IN_PROGRESS", "WAITING_REQUESTER"];

const ORDERING_OPTIONS = [
  { value: "-created_at", label: "Mais recentes" },
  { value: "created_at", label: "Mais antigos" },
  { value: "-updated_at", label: "Atualizados recentemente" },
  { value: "-priority", label: "Maior prioridade" },
];

/** Lê os filtros da URL (fonte da verdade da tela). */
function readFilters(params: URLSearchParams): TicketFilters {
  const number = (key: string) => (params.get(key) ? Number(params.get(key)) : undefined);
  return {
    search: params.get("search") ?? undefined,
    status: params.getAll("status") as TicketStatus[],
    priority: params.getAll("priority").map(Number) as Priority[],
    category: number("category"),
    assignee: number("assignee"),
    requester: number("requester"),
    unassigned: params.get("unassigned") === "true" ? true : undefined,
    ordering: params.get("ordering") ?? "-created_at",
    page: number("page") ?? 1,
    page_size: PAGE_SIZE,
  };
}

/** "active" | "all" | um status | "custom" — para o select de status. */
function statusSelectValue(statuses: TicketStatus[]): string {
  if (statuses.length === 0) return "all";
  if (statuses.length === 1) return statuses[0]!;
  const sameAsActive =
    statuses.length === ACTIVE.length && ACTIVE.every((s) => statuses.includes(s));
  return sameAsActive ? "active" : "custom";
}

function TicketRowMeta({ ticket }: { ticket: Ticket }) {
  return (
    <span className="text-xs text-slate-500">
      #{ticket.id} · {ticket.category_name}
    </span>
  );
}

function AssigneeCell({ ticket }: { ticket: Ticket }) {
  if (!ticket.assignee) return <span className="text-sm text-slate-400">Sem responsável</span>;
  return (
    <span className="flex items-center gap-2 text-sm text-slate-700">
      <Avatar name={ticket.assignee.full_name} />
      <span className="truncate">{ticket.assignee.full_name}</span>
    </span>
  );
}

export function TicketListPage() {
  const user = useCurrentUser();
  const isStaff = user.role !== "REQUESTER";
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const filters = readFilters(params);

  // Campo de busca com atraso, para não chamar a API a cada tecla.
  const [searchText, setSearchText] = useState(filters.search ?? "");
  const debouncedSearch = useDebounce(searchText);

  const update = (changes: Record<string, string | string[] | undefined>) => {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      next.delete(key);
      if (Array.isArray(value)) value.forEach((v) => next.append(key, v));
      else if (value) next.set(key, value);
    }
    if (!("page" in changes)) next.delete("page"); // filtro novo → volta à página 1
    setParams(next, { replace: true });
  };

  // Quando o texto digitado "assenta", leva a busca para a URL (o que dispara a consulta).
  useEffect(() => {
    if ((filters.search ?? "") !== debouncedSearch) update({ search: debouncedSearch || undefined });
  }, [debouncedSearch]); // só reage ao texto; `update` lê os parâmetros atuais da URL

  const tickets = useQuery({
    queryKey: ["tickets", filters],
    queryFn: () => ticketsApi.list(filters),
    placeholderData: keepPreviousData, // mantém a página anterior visível enquanto carrega
  });
  const categories = useQuery({ queryKey: ["categories"], queryFn: categoriesApi.list });
  const technicians = useQuery({
    queryKey: ["technicians"],
    queryFn: usersApi.technicians,
    enabled: isStaff, // o endpoint é só para técnicos/admins
  });

  const hasFilters = [...params.keys()].some((k) => k !== "ordering" && k !== "page");
  const statusValue = statusSelectValue(filters.status ?? []);
  const assigneeValue = filters.unassigned ? "none" : filters.assignee ? String(filters.assignee) : "";

  const onStatusChange = (value: string) => {
    if (value === "all") update({ status: undefined });
    else if (value === "active") update({ status: ACTIVE });
    else update({ status: [value] });
  };

  const onAssigneeChange = (value: string) => {
    if (value === "none") update({ unassigned: "true", assignee: undefined });
    else update({ unassigned: undefined, assignee: value || undefined });
  };

  const data = tickets.data;
  const page = filters.page ?? 1;
  const totalPages = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1;

  return (
    <>
      <PageHeader
        title={user.role === "REQUESTER" ? "Meus chamados" : "Chamados"}
        description={data ? `${data.count} chamado${data.count === 1 ? "" : "s"} encontrado${data.count === 1 ? "" : "s"}` : undefined}
        actions={
          <Link to="/tickets/new">
            <Button icon={<Plus className="size-4" />}>Abrir chamado</Button>
          </Link>
        }
      />

      <Card>
        {/* Barra de filtros */}
        <div className="grid grid-cols-1 gap-3 border-b border-slate-200 p-4 sm:grid-cols-2 lg:grid-cols-6">
          <div className="relative sm:col-span-2">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" aria-hidden />
            <input
              type="search"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder="Buscar por título, descrição ou nº"
              aria-label="Buscar chamados"
              className={`${inputClass} pl-9`}
            />
          </div>
          <select
            aria-label="Filtrar por status"
            className={inputClass}
            value={statusValue}
            onChange={(e) => onStatusChange(e.target.value)}
          >
            <option value="all">Todos os status</option>
            <option value="active">Ativos</option>
            {statusValue === "custom" && <option value="custom">Seleção personalizada</option>}
            {STATUS_ORDER.map((s) => (
              <option key={s} value={s}>
                {STATUS_META[s].label}
              </option>
            ))}
          </select>
          <select
            aria-label="Filtrar por prioridade"
            className={inputClass}
            value={filters.priority?.length === 1 ? String(filters.priority[0]) : ""}
            onChange={(e) => update({ priority: e.target.value ? [e.target.value] : undefined })}
          >
            <option value="">Todas as prioridades</option>
            {[...PRIORITIES].reverse().map((p) => (
              <option key={p} value={p}>
                {PRIORITY_META[p].label}
              </option>
            ))}
          </select>
          <select
            aria-label="Filtrar por categoria"
            className={inputClass}
            value={filters.category ? String(filters.category) : ""}
            onChange={(e) => update({ category: e.target.value || undefined })}
          >
            <option value="">Todas as categorias</option>
            {categories.data?.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          {isStaff ? (
            <select
              aria-label="Filtrar por responsável"
              className={inputClass}
              value={assigneeValue}
              onChange={(e) => onAssigneeChange(e.target.value)}
            >
              <option value="">Todos os responsáveis</option>
              <option value="none">Sem responsável</option>
              <option value={user.id}>Atribuídos a mim</option>
              {technicians.data
                ?.filter((t) => t.id !== user.id)
                .map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.full_name}
                  </option>
                ))}
            </select>
          ) : (
            <div className="hidden lg:block" />
          )}
          <div className="flex items-center gap-2 sm:col-span-2 lg:col-span-6">
            <label htmlFor="ordering" className="text-sm text-slate-500">
              Ordenar por
            </label>
            <select
              id="ordering"
              className={`${inputClass} w-auto`}
              value={filters.ordering}
              onChange={(e) => update({ ordering: e.target.value })}
            >
              {ORDERING_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            {hasFilters && (
              <Button
                variant="ghost"
                className="ml-auto"
                icon={<X className="size-4" />}
                onClick={() => {
                  setSearchText("");
                  setParams(new URLSearchParams(), { replace: true });
                }}
              >
                Limpar filtros
              </Button>
            )}
          </div>
        </div>

        {/* Resultados */}
        {tickets.isPending ? (
          <LoadingState label="Carregando chamados..." />
        ) : tickets.isError ? (
          <ErrorState message={errorMessage(tickets.error)} onRetry={() => void tickets.refetch()} />
        ) : data!.results.length === 0 ? (
          <EmptyState
            title={hasFilters ? "Nenhum chamado encontrado" : "Nenhum chamado ainda"}
            description={
              hasFilters
                ? "Tente ajustar a busca ou limpar os filtros."
                : "Quando um chamado for aberto, ele aparecerá aqui."
            }
          />
        ) : (
          <div className={tickets.isFetching ? "opacity-60 transition-opacity" : undefined}>
            {/* Desktop: tabela */}
            <table className="hidden w-full text-left md:table">
              <thead className="border-b border-slate-200 bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-500">
                <tr>
                  <th scope="col" className="px-4 py-3">Chamado</th>
                  <th scope="col" className="px-4 py-3">Status</th>
                  <th scope="col" className="px-4 py-3">Prioridade</th>
                  {isStaff && <th scope="col" className="px-4 py-3">Solicitante</th>}
                  <th scope="col" className="px-4 py-3">Responsável</th>
                  <th scope="col" className="px-4 py-3 text-right">Atualizado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data!.results.map((t) => (
                  <tr
                    key={t.id}
                    onClick={() => navigate(`/tickets/${t.id}`)}
                    className="cursor-pointer hover:bg-slate-50"
                  >
                    <td className="max-w-md px-4 py-3">
                      <Link
                        to={`/tickets/${t.id}`}
                        className="block truncate text-sm font-medium text-slate-900 hover:text-indigo-600"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {t.title}
                      </Link>
                      <TicketRowMeta ticket={t} />
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={t.status} /></td>
                    <td className="px-4 py-3"><PriorityBadge priority={t.priority} /></td>
                    {isStaff && (
                      <td className="max-w-40 truncate px-4 py-3 text-sm text-slate-700">
                        {t.requester.full_name}
                      </td>
                    )}
                    <td className="max-w-48 px-4 py-3"><AssigneeCell ticket={t} /></td>
                    <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-slate-500">
                      <time dateTime={t.updated_at}>{formatRelative(t.updated_at)}</time>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Mobile: cartões */}
            <ul className="divide-y divide-slate-100 md:hidden">
              {data!.results.map((t) => (
                <li key={t.id}>
                  <Link to={`/tickets/${t.id}`} className="block px-4 py-3 hover:bg-slate-50">
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm font-medium text-slate-900">{t.title}</p>
                      <StatusBadge status={t.status} />
                    </div>
                    <TicketRowMeta ticket={t} />
                    <div className="mt-2 flex items-center justify-between">
                      <PriorityBadge priority={t.priority} />
                      <span className="text-xs text-slate-500">{formatRelative(t.updated_at)}</span>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Paginação */}
        {data && data.count > 0 && (
          <nav
            aria-label="Paginação"
            className="flex items-center justify-between gap-3 border-t border-slate-200 px-4 py-3"
          >
            <p className="text-sm text-slate-500">
              {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, data.count)} de {data.count}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                disabled={!data.previous}
                onClick={() => update({ page: String(page - 1) })}
                icon={<ChevronLeft className="size-4" />}
                aria-label="Página anterior"
              >
                <span className="hidden sm:inline">Anterior</span>
              </Button>
              <span className="text-sm text-slate-600">
                {page} / {totalPages}
              </span>
              <Button
                variant="secondary"
                disabled={!data.next}
                onClick={() => update({ page: String(page + 1) })}
                aria-label="Próxima página"
              >
                <span className="hidden sm:inline">Próxima</span>
                <ChevronRight className="size-4" />
              </Button>
            </div>
          </nav>
        )}
      </Card>
    </>
  );
}
