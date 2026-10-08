import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { AlertTriangle, CheckCircle2, Clock, Inbox, Plus, UserCheck } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { errorMessage } from "../api/client";
import { dashboardApi } from "../api/endpoints";
import type { DashboardSummary } from "../api/types";
import { useCurrentUser } from "../auth/AuthContext";
import { Button, Card, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { PRIORITY_META, STATUS_META } from "../lib/labels";

function formatHours(hours: number | null): string {
  if (hours === null) return "—";
  if (hours < 1) return `${Math.round(hours * 60)} min`;
  if (hours < 48) return `${hours.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} h`;
  return `${(hours / 24).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} dias`;
}

function StatCard({
  label,
  value,
  icon,
  to,
  hint,
}: {
  label: string;
  value: ReactNode;
  icon: ReactNode;
  to?: string;
  hint?: string;
}) {
  const body = (
    <Card className={clsx("h-full p-5", to && "transition-shadow hover:shadow-md")}>
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <span className="text-slate-400">{icon}</span>
      </div>
      <p className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </Card>
  );
  return to ? (
    <Link to={to} className="block rounded-lg focus-visible:outline-2 focus-visible:outline-indigo-600">
      {body}
    </Link>
  ) : (
    body
  );
}

function BarList({
  title,
  rows,
  emptyText,
}: {
  title: string;
  rows: Array<{ key: string; label: string; count: number; color: string; to: string }>;
  emptyText: string;
}) {
  const max = Math.max(1, ...rows.map((r) => r.count));
  const hasData = rows.some((r) => r.count > 0);
  return (
    <Card className="p-5">
      <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
      {hasData ? (
        <ul className="mt-4 space-y-3">
          {rows.map((row) => (
            <li key={row.key}>
              <Link to={row.to} className="group block">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-600 group-hover:text-slate-900">{row.label}</span>
                  <span className="font-medium tabular-nums text-slate-900">{row.count}</span>
                </div>
                <div className="mt-1.5 h-2 rounded-full bg-slate-100">
                  <div
                    className={clsx("h-2 rounded-full", row.color)}
                    style={{ width: `${(row.count / max) * 100}%` }}
                  />
                </div>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-sm text-slate-500">{emptyText}</p>
      )}
    </Card>
  );
}

function Dashboard({ data }: { data: DashboardSummary }) {
  const user = useCurrentUser();
  const isRequester = user.role === "REQUESTER";
  const waiting = data.by_status.find((s) => s.status === "WAITING_REQUESTER")?.count ?? 0;

  return (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label={isRequester ? "Meus chamados ativos" : "Chamados ativos"}
          value={data.open}
          icon={<Inbox className="size-5" />}
          to="/tickets?status=OPEN&status=IN_PROGRESS&status=WAITING_REQUESTER"
          hint="Abertos, em atendimento ou aguardando"
        />
        {isRequester ? (
          <StatCard
            label="Aguardando sua resposta"
            value={waiting}
            icon={<AlertTriangle className="size-5" />}
            to="/tickets?status=WAITING_REQUESTER"
          />
        ) : (
          <StatCard
            label="Sem responsável"
            value={data.unassigned}
            icon={<AlertTriangle className="size-5" />}
            to="/tickets?unassigned=true&status=OPEN&status=IN_PROGRESS&status=WAITING_REQUESTER"
            hint="Fila aguardando um técnico"
          />
        )}
        {user.role === "TECHNICIAN" ? (
          <StatCard
            label="Atribuídos a mim"
            value={data.assigned_to_me}
            icon={<UserCheck className="size-5" />}
            to={`/tickets?assignee=${user.id}&status=IN_PROGRESS&status=WAITING_REQUESTER&status=OPEN`}
          />
        ) : (
          <StatCard
            label="Resolvidos (30 dias)"
            value={data.resolved_last_30_days}
            icon={<CheckCircle2 className="size-5" />}
          />
        )}
        <StatCard
          label="Tempo médio de resolução"
          value={formatHours(data.avg_resolution_hours)}
          icon={<Clock className="size-5" />}
          hint="Chamados resolvidos nos últimos 30 dias"
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <BarList
          title="Por status"
          emptyText="Nenhum chamado ainda."
          rows={data.by_status.map((s) => ({
            key: s.status,
            label: s.label,
            count: s.count,
            color: STATUS_META[s.status].dot,
            to: `/tickets?status=${s.status}`,
          }))}
        />
        <BarList
          title="Por prioridade"
          emptyText="Nenhum chamado ainda."
          rows={[...data.by_priority].reverse().map((p) => ({
            key: String(p.priority),
            label: p.label,
            count: p.count,
            color: PRIORITY_META[p.priority].bar,
            to: `/tickets?priority=${p.priority}`,
          }))}
        />
        <BarList
          title="Ativos por categoria"
          emptyText="Nenhum chamado ativo."
          rows={data.open_by_category.map((c) => ({
            key: String(c.id),
            label: c.name,
            count: c.count,
            color: "bg-indigo-500",
            to: `/tickets?category=${c.id}&status=OPEN&status=IN_PROGRESS&status=WAITING_REQUESTER`,
          }))}
        />
      </div>
    </>
  );
}

export function DashboardPage() {
  const user = useCurrentUser();
  const query = useQuery({ queryKey: ["dashboard"], queryFn: dashboardApi.summary });

  return (
    <>
      <PageHeader
        title={`Olá, ${user.first_name}`}
        description={
          user.role === "REQUESTER"
            ? "Acompanhe seus chamados de suporte."
            : "Visão geral do atendimento."
        }
        actions={
          <Link to="/tickets/new">
            <Button icon={<Plus className="size-4" />}>Abrir chamado</Button>
          </Link>
        }
      />
      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
      ) : (
        <Dashboard data={query.data} />
      )}
    </>
  );
}
