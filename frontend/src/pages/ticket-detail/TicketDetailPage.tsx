import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { ArrowLeft, Pencil } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, errorMessage } from "../../api/client";
import { ticketsApi } from "../../api/endpoints";
import type { Ticket } from "../../api/types";
import {
  Avatar,
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  PriorityBadge,
  StatusBadge,
} from "../../components/ui";
import { formatDateTime } from "../../lib/labels";
import { CommentsSection } from "./CommentsSection";
import { EditTicketForm } from "./EditTicketForm";
import { HistorySection } from "./HistorySection";
import { TicketActions } from "./TicketActions";

function DetailRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2.5">
      <dt className="text-sm text-slate-500">{label}</dt>
      <dd className="min-w-0 text-right text-sm text-slate-900">{children}</dd>
    </div>
  );
}

function Person({ name }: { name: string }) {
  return (
    <span className="inline-flex max-w-full items-center gap-2">
      <Avatar name={name} />
      <span className="truncate">{name}</span>
    </span>
  );
}

function DetailsCard({ ticket }: { ticket: Ticket }) {
  return (
    <Card className="p-5">
      <h2 className="text-sm font-semibold text-slate-900">Detalhes</h2>
      <dl className="mt-2 divide-y divide-slate-100">
        <DetailRow label="Status"><StatusBadge status={ticket.status} /></DetailRow>
        <DetailRow label="Prioridade"><PriorityBadge priority={ticket.priority} /></DetailRow>
        <DetailRow label="Categoria">{ticket.category_name}</DetailRow>
        <DetailRow label="Solicitante"><Person name={ticket.requester.full_name} /></DetailRow>
        <DetailRow label="Responsável">
          {ticket.assignee ? (
            <Person name={ticket.assignee.full_name} />
          ) : (
            <span className="text-slate-400">Sem responsável</span>
          )}
        </DetailRow>
        <DetailRow label="Aberto em">{formatDateTime(ticket.created_at)}</DetailRow>
        <DetailRow label="Atualizado em">{formatDateTime(ticket.updated_at)}</DetailRow>
        {ticket.resolved_at && (
          <DetailRow label="Resolvido em">{formatDateTime(ticket.resolved_at)}</DetailRow>
        )}
        {ticket.closed_at && <DetailRow label="Encerrado em">{formatDateTime(ticket.closed_at)}</DetailRow>}
      </dl>
    </Card>
  );
}

type Tab = "comments" | "history";

export function TicketDetailPage() {
  const id = Number(useParams().id);
  const [editing, setEditing] = useState(false);
  const [tab, setTab] = useState<Tab>("comments");

  const query = useQuery({
    queryKey: ["ticket", id],
    queryFn: () => ticketsApi.get(id),
    enabled: Number.isInteger(id) && id > 0,
  });

  if (!Number.isInteger(id) || id <= 0 || (query.error instanceof ApiError && query.error.status === 404)) {
    return (
      <EmptyState
        title="Chamado não encontrado"
        description="Ele não existe ou você não tem acesso a ele."
        action={
          <Link to="/tickets" className="text-sm font-semibold text-indigo-600 hover:text-indigo-500">
            Voltar para os chamados
          </Link>
        }
      />
    );
  }
  if (query.isPending) return <LoadingState label="Carregando chamado..." />;
  if (query.isError) {
    return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  }

  const ticket = query.data;
  const canEdit = ticket.permissions.editable_fields.length > 0;

  return (
    <>
      <Link
        to="/tickets"
        className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-900"
      >
        <ArrowLeft className="size-4" aria-hidden /> Chamados
      </Link>

      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-500">Chamado #{ticket.id}</p>
          <h1 className="mt-1 break-words text-xl font-semibold tracking-tight text-slate-900 sm:text-2xl">
            {ticket.title}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <StatusBadge status={ticket.status} />
            <PriorityBadge priority={ticket.priority} />
          </div>
        </div>
        {canEdit && !editing && (
          <Button variant="secondary" icon={<Pencil className="size-4" />} onClick={() => setEditing(true)}>
            Editar
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card className="p-5 sm:p-6">
            {editing ? (
              <EditTicketForm ticket={ticket} onDone={() => setEditing(false)} />
            ) : (
              <>
                <h2 className="text-sm font-semibold text-slate-900">Descrição</h2>
                <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-slate-700">
                  {ticket.description}
                </p>
              </>
            )}
          </Card>

          <Card>
            <div role="tablist" aria-label="Atividade do chamado" className="flex border-b border-slate-200 px-2">
              {(
                [
                  ["comments", "Comentários"],
                  ["history", "Histórico"],
                ] as const
              ).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  role="tab"
                  id={`tab-${value}`}
                  aria-selected={tab === value}
                  aria-controls={`panel-${value}`}
                  onClick={() => setTab(value)}
                  className={clsx(
                    "-mb-px border-b-2 px-4 py-3 text-sm font-medium",
                    tab === value
                      ? "border-indigo-600 text-indigo-600"
                      : "border-transparent text-slate-500 hover:text-slate-700",
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
            <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="p-5 sm:p-6">
              {tab === "comments" ? <CommentsSection ticket={ticket} /> : <HistorySection ticketId={ticket.id} />}
            </div>
          </Card>
        </div>

        <aside className="space-y-6">
          <TicketActions ticket={ticket} />
          <DetailsCard ticket={ticket} />
        </aside>
      </div>
    </>
  );
}
