import { useQuery } from "@tanstack/react-query";
import { errorMessage } from "../../api/client";
import { ticketsApi } from "../../api/endpoints";
import type { HistoryEntry } from "../../api/types";
import { ErrorState, LoadingState } from "../../components/ui";
import { FIELD_LABEL, formatDateTime } from "../../lib/labels";

function describe(entry: HistoryEntry) {
  const field = FIELD_LABEL[entry.field]?.toLowerCase() ?? entry.field;
  switch (entry.action) {
    case "CREATED":
      return <>abriu o chamado</>;
    case "ASSIGNED":
      return entry.old_value ? (
        <>
          reatribuiu de <strong>{entry.old_value}</strong> para <strong>{entry.new_value}</strong>
        </>
      ) : (
        <>
          atribuiu a <strong>{entry.new_value}</strong>
        </>
      );
    case "STATUS_CHANGED":
      return (
        <>
          mudou o status de <strong>{entry.old_value}</strong> para <strong>{entry.new_value}</strong>
        </>
      );
    default:
      // Descrição pode ser longa: não repete o texto inteiro na linha do tempo.
      return entry.field === "description" ? (
        <>alterou a descrição</>
      ) : (
        <>
          alterou {field} de <strong>{entry.old_value || "—"}</strong> para{" "}
          <strong>{entry.new_value || "—"}</strong>
        </>
      );
  }
}

export function HistorySection({ ticketId }: { ticketId: number }) {
  const history = useQuery({
    queryKey: ["ticket", ticketId, "history"],
    queryFn: () => ticketsApi.history(ticketId),
  });

  if (history.isPending) return <LoadingState label="Carregando histórico..." />;
  if (history.isError) {
    return <ErrorState message={errorMessage(history.error)} onRetry={() => void history.refetch()} />;
  }

  return (
    <ol className="relative ml-2 border-l border-slate-200">
      {history.data.map((entry) => (
        <li key={entry.id} className="mb-5 ml-5 last:mb-0">
          <span className="absolute -left-1.5 mt-1.5 size-3 rounded-full border-2 border-white bg-slate-300" aria-hidden />
          <p className="text-sm text-slate-700">
            <span className="font-medium text-slate-900">{entry.actor.full_name}</span> {describe(entry)}
          </p>
          <time className="text-xs text-slate-500" dateTime={entry.created_at}>
            {formatDateTime(entry.created_at)}
          </time>
        </li>
      ))}
    </ol>
  );
}
