import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { Lock } from "lucide-react";
import { useState } from "react";
import { errorMessage } from "../../api/client";
import { ticketsApi } from "../../api/endpoints";
import type { Ticket } from "../../api/types";
import { useToast } from "../../components/Toaster";
import { Avatar, Button, ErrorState, LoadingState, inputClass } from "../../components/ui";
import { formatDateTime, formatRelative } from "../../lib/labels";

export function CommentsSection({ ticket }: { ticket: Ticket }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [body, setBody] = useState("");
  const [isInternal, setIsInternal] = useState(false);
  const comments = useQuery({
    queryKey: ["ticket", ticket.id, "comments"],
    queryFn: () => ticketsApi.comments(ticket.id),
  });

  const add = useMutation({
    mutationFn: () => ticketsApi.addComment(ticket.id, body.trim(), isInternal),
    onSuccess: () => {
      setBody("");
      setIsInternal(false);
      void queryClient.invalidateQueries({ queryKey: ["ticket", ticket.id, "comments"] });
      void queryClient.invalidateQueries({ queryKey: ["tickets"] });
      toast.success("Comentário adicionado.");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const { can_comment, can_comment_internal } = ticket.permissions;

  return (
    <section aria-labelledby="comments-title">
      <h2 id="comments-title" className="sr-only">
        Comentários
      </h2>
      {comments.isPending ? (
        <LoadingState label="Carregando comentários..." />
      ) : comments.isError ? (
        <ErrorState message={errorMessage(comments.error)} onRetry={() => void comments.refetch()} />
      ) : comments.data.length === 0 ? (
        <p className="py-6 text-center text-sm text-slate-500">Nenhum comentário ainda.</p>
      ) : (
        <ul className="space-y-4">
          {comments.data.map((comment) => (
            <li key={comment.id} className="flex gap-3">
              <Avatar name={comment.author.full_name} size="md" />
              <div
                className={clsx(
                  "min-w-0 flex-1 rounded-lg px-4 py-3 ring-1",
                  comment.is_internal ? "bg-amber-50 ring-amber-200" : "bg-white ring-slate-200",
                )}
              >
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  <span className="text-sm font-medium text-slate-900">{comment.author.full_name}</span>
                  {comment.is_internal && (
                    <span className="inline-flex items-center gap-1 rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-800">
                      <Lock className="size-3" aria-hidden /> Nota interna
                    </span>
                  )}
                  <time
                    className="text-xs text-slate-500"
                    dateTime={comment.created_at}
                    title={formatDateTime(comment.created_at)}
                  >
                    {formatRelative(comment.created_at)}
                  </time>
                </div>
                <p className="mt-1 whitespace-pre-wrap break-words text-sm text-slate-700">{comment.body}</p>
              </div>
            </li>
          ))}
        </ul>
      )}

      {can_comment ? (
        <form
          className="mt-6"
          onSubmit={(e) => {
            e.preventDefault();
            if (body.trim()) add.mutate();
          }}
        >
          <label htmlFor="comment" className="sr-only">
            Novo comentário
          </label>
          <textarea
            id="comment"
            rows={3}
            maxLength={5000}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder={isInternal ? "Nota visível apenas para a equipe de suporte..." : "Escreva um comentário..."}
            className={clsx(inputClass, isInternal && "bg-amber-50/50")}
          />
          <div className="mt-3 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
            {can_comment_internal ? (
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={isInternal}
                  onChange={(e) => setIsInternal(e.target.checked)}
                  className="size-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-600"
                />
                Nota interna (o solicitante não vê)
              </label>
            ) : (
              <span />
            )}
            <Button type="submit" loading={add.isPending} disabled={!body.trim()}>
              {isInternal ? "Adicionar nota" : "Comentar"}
            </Button>
          </div>
        </form>
      ) : (
        <p className="mt-6 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-500">
          Este chamado está encerrado e não aceita novos comentários.
        </p>
      )}
    </section>
  );
}
