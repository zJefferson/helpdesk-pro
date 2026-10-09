import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { ApiError } from "../../api/client";
import { categoriesApi, ticketsApi, type TicketInput } from "../../api/endpoints";
import type { Priority, Ticket } from "../../api/types";
import { Button, Field, inputClass } from "../../components/ui";
import { PRIORITIES, PRIORITY_META } from "../../lib/labels";
import { ticketFields } from "../../lib/ticketSchema";
import { useTicketMutation } from "./useTicketMutation";

const schema = z.object(ticketFields);
type FormInput = z.input<typeof schema>;
type FormOutput = z.output<typeof schema>;

/** Edição só dos campos que o backend informou como editáveis para este usuário. */
export function EditTicketForm({ ticket, onDone }: { ticket: Ticket; onDone: () => void }) {
  const editable = new Set(ticket.permissions.editable_fields);
  const categories = useQuery({ queryKey: ["categories"], queryFn: categoriesApi.list });

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, dirtyFields },
  } = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: ticket.title,
      description: ticket.description,
      category: String(ticket.category),
      priority: String(ticket.priority),
    },
  });

  const update = useTicketMutation(
    ticket.id,
    (data: Partial<TicketInput>) => ticketsApi.update(ticket.id, data),
    "Chamado atualizado.",
  );

  const onSubmit = (data: FormOutput) => {
    // Envia só o que mudou E é editável: o backend recusaria qualquer outro campo.
    const changes: Partial<TicketInput> = {};
    for (const field of editable) {
      if (dirtyFields[field]) {
        (changes as Record<string, unknown>)[field] =
          field === "priority" ? (data.priority as Priority) : data[field];
      }
    }
    if (Object.keys(changes).length === 0) return onDone();
    update.mutate(changes, {
      onSuccess: onDone,
      onError: (error) => {
        if (error instanceof ApiError) {
          for (const [field, message] of Object.entries(error.fieldErrors)) {
            if (field in schema.shape) setError(field as keyof FormInput, { message });
          }
        }
      },
    });
  };

  // A categoria atual pode estar inativa: mantém ela visível na lista.
  const categoryOptions = categories.data ?? [];
  const hasCurrentCategory = categoryOptions.some((c) => c.id === ticket.category);

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
      <Field label="Título" htmlFor="edit-title" error={errors.title?.message}>
        <input
          id="edit-title"
          className={inputClass}
          disabled={!editable.has("title")}
          aria-invalid={!!errors.title}
          {...register("title")}
        />
      </Field>
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <Field label="Categoria" htmlFor="edit-category" error={errors.category?.message}>
          <select
            id="edit-category"
            className={inputClass}
            disabled={!editable.has("category")}
            {...register("category")}
          >
            {!hasCurrentCategory && <option value={ticket.category}>{ticket.category_name}</option>}
            {categoryOptions.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </Field>
        <Field
          label="Prioridade"
          htmlFor="edit-priority"
          hint={editable.has("priority") ? undefined : "Definida pela equipe de suporte."}
        >
          <select
            id="edit-priority"
            className={inputClass}
            disabled={!editable.has("priority")}
            {...register("priority")}
          >
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {PRIORITY_META[p].label}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <Field label="Descrição" htmlFor="edit-description" error={errors.description?.message}>
        <textarea
          id="edit-description"
          rows={6}
          className={inputClass}
          disabled={!editable.has("description")}
          aria-invalid={!!errors.description}
          {...register("description")}
        />
      </Field>
      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onDone} disabled={update.isPending}>
          Cancelar
        </Button>
        <Button type="submit" loading={update.isPending}>
          Salvar alterações
        </Button>
      </div>
    </form>
  );
}
