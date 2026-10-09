import { useQuery } from "@tanstack/react-query";
import { UserPlus } from "lucide-react";
import { useState } from "react";
import { ticketsApi, usersApi } from "../../api/endpoints";
import type { Ticket, TicketStatus } from "../../api/types";
import { useCurrentUser } from "../../auth/AuthContext";
import { Button, Card, inputClass } from "../../components/ui";
import { STATUS_META, transitionLabel } from "../../lib/labels";
import { useTicketMutation } from "./useTicketMutation";

const DESTRUCTIVE: TicketStatus[] = ["CANCELLED"];

/** Ações disponíveis — exibidas conforme `ticket.permissions`, calculado pelo backend. */
export function TicketActions({ ticket }: { ticket: Ticket }) {
  const user = useCurrentUser();
  const { permissions } = ticket;
  const [confirming, setConfirming] = useState<TicketStatus | null>(null);
  const [selectedTech, setSelectedTech] = useState("");

  const changeStatus = useTicketMutation(
    ticket.id,
    (status: TicketStatus) => ticketsApi.changeStatus(ticket.id, status),
    "Status atualizado.",
  );
  const assign = useTicketMutation(
    ticket.id,
    (assigneeId: number) => ticketsApi.assign(ticket.id, assigneeId),
    "Responsável atualizado.",
  );
  const technicians = useQuery({
    queryKey: ["technicians"],
    queryFn: usersApi.technicians,
    enabled: permissions.can_assign,
  });

  const hasActions =
    permissions.status_transitions.length > 0 || permissions.can_assign || permissions.can_take;
  if (!hasActions) return null;

  const onTransition = (status: TicketStatus) => {
    if (DESTRUCTIVE.includes(status) && confirming !== status) {
      setConfirming(status);
      return;
    }
    setConfirming(null);
    changeStatus.mutate(status);
  };

  return (
    <Card className="p-5">
      <h2 className="text-sm font-semibold text-slate-900">Ações</h2>

      {permissions.status_transitions.length > 0 && (
        <div className="mt-4 flex flex-col gap-2">
          {permissions.status_transitions.map((status) => (
            <Button
              key={status}
              variant={DESTRUCTIVE.includes(status) ? "danger" : status === "IN_PROGRESS" || status === "RESOLVED" || status === "CLOSED" ? "primary" : "secondary"}
              loading={changeStatus.isPending && changeStatus.variables === status}
              disabled={changeStatus.isPending}
              onClick={() => onTransition(status)}
            >
              {confirming === status ? `Confirmar: ${STATUS_META[status].label.toLowerCase()}?` : transitionLabel(ticket.status, status)}
            </Button>
          ))}
          {confirming && (
            <Button variant="ghost" onClick={() => setConfirming(null)}>
              Voltar
            </Button>
          )}
        </div>
      )}

      {permissions.can_take && (
        <Button
          className="mt-4 w-full"
          variant="secondary"
          icon={<UserPlus className="size-4" />}
          loading={assign.isPending}
          onClick={() => assign.mutate(user.id)}
        >
          Assumir chamado
        </Button>
      )}

      {permissions.can_assign && (
        <form
          className="mt-4 space-y-2 border-t border-slate-100 pt-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (selectedTech) assign.mutate(Number(selectedTech));
          }}
        >
          <label htmlFor="assignee" className="block text-sm font-medium text-slate-700">
            {ticket.assignee ? "Reatribuir para" : "Atribuir para"}
          </label>
          <select
            id="assignee"
            className={inputClass}
            value={selectedTech}
            onChange={(e) => setSelectedTech(e.target.value)}
            disabled={technicians.isPending}
          >
            <option value="">{technicians.isPending ? "Carregando técnicos..." : "Selecione um técnico"}</option>
            {technicians.data
              ?.filter((t) => t.id !== ticket.assignee?.id)
              .map((t) => (
                <option key={t.id} value={t.id}>
                  {t.full_name}
                </option>
              ))}
          </select>
          <Button
            type="submit"
            variant="secondary"
            className="w-full"
            disabled={!selectedTech}
            loading={assign.isPending}
          >
            Atribuir
          </Button>
        </form>
      )}
    </Card>
  );
}
