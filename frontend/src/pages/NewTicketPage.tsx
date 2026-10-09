import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { ApiError, errorMessage } from "../api/client";
import { categoriesApi, ticketsApi } from "../api/endpoints";
import type { Priority } from "../api/types";
import { useToast } from "../components/Toaster";
import {
  Button,
  ButtonLink,
  Card,
  ErrorState,
  Field,
  LoadingState,
  PageHeader,
  inputClass,
} from "../components/ui";
import { PRIORITIES, PRIORITY_META } from "../lib/labels";
import { newTicketSchema, type NewTicketData, type NewTicketForm } from "../lib/ticketSchema";

export function NewTicketPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();
  const categories = useQuery({ queryKey: ["categories"], queryFn: categoriesApi.list });

  const {
    register,
    handleSubmit,
    setError,
    watch,
    formState: { errors },
  } = useForm<NewTicketForm, unknown, NewTicketData>({
    resolver: zodResolver(newTicketSchema),
    defaultValues: { title: "", description: "", category: "", priority: "2" },
  });

  const create = useMutation({
    mutationFn: (data: NewTicketData) =>
      ticketsApi.create({ ...data, priority: data.priority as Priority }),
    onSuccess: (ticket) => {
      // A lista e o dashboard mudaram: marca os dados em cache como desatualizados.
      void queryClient.invalidateQueries({ queryKey: ["tickets"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(`Chamado #${ticket.id} aberto com sucesso.`);
      navigate(`/tickets/${ticket.id}`);
    },
    onError: (error) => {
      // Erros de validação do backend aparecem no campo correspondente.
      if (error instanceof ApiError && error.status === 400) {
        for (const [field, message] of Object.entries(error.fieldErrors)) {
          if (field in newTicketSchema.shape) {
            setError(field as keyof NewTicketForm, { message });
          }
        }
      }
      toast.error(errorMessage(error));
    },
  });

  const descriptionLength = watch("description")?.length ?? 0;

  if (categories.isPending) return <LoadingState />;
  if (categories.isError) {
    return <ErrorState message={errorMessage(categories.error)} onRetry={() => void categories.refetch()} />;
  }

  return (
    <>
      <PageHeader
        title="Abrir chamado"
        description="Descreva o problema com detalhes para agilizar o atendimento."
      />
      <Card className="max-w-3xl">
        <form onSubmit={handleSubmit((data) => create.mutate(data))} noValidate className="space-y-6 p-6">
          <Field label="Título" htmlFor="title" error={errors.title?.message} hint="Um resumo curto do problema.">
            <input
              id="title"
              className={inputClass}
              placeholder="Ex.: Impressora do 2º andar não imprime"
              maxLength={150}
              aria-invalid={!!errors.title}
              aria-describedby={errors.title ? "title-error" : undefined}
              {...register("title")}
            />
          </Field>

          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <Field label="Categoria" htmlFor="category" error={errors.category?.message}>
              <select
                id="category"
                className={inputClass}
                aria-invalid={!!errors.category}
                {...register("category")}
              >
                <option value="">Selecione...</option>
                {categories.data.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Prioridade" htmlFor="priority" error={errors.priority?.message}>
              <select id="priority" className={inputClass} {...register("priority")}>
                {PRIORITIES.map((p) => (
                  <option key={p} value={p}>
                    {PRIORITY_META[p].label}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <Field
            label="Descrição"
            htmlFor="description"
            error={errors.description?.message}
            hint={`${descriptionLength}/5000 — inclua o que aconteceu, desde quando e o que já tentou.`}
          >
            <textarea
              id="description"
              rows={7}
              className={inputClass}
              maxLength={5000}
              aria-invalid={!!errors.description}
              aria-describedby={errors.description ? "description-error" : undefined}
              {...register("description")}
            />
          </Field>

          {categories.data.length === 0 && (
            <p className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
              Nenhuma categoria ativa cadastrada. Peça a um administrador para cadastrar categorias.
            </p>
          )}

          <div className="flex flex-col-reverse gap-3 border-t border-slate-200 pt-6 sm:flex-row sm:justify-end">
            <ButtonLink to="/tickets" variant="secondary">
              Cancelar
            </ButtonLink>
            <Button type="submit" loading={create.isPending}>
              Abrir chamado
            </Button>
          </div>
        </form>
      </Card>
    </>
  );
}
