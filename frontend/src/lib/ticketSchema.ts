import { z } from "zod";

// Mesmas regras de tamanho do backend (apps/tickets/models.py). A validação aqui só
// dá retorno imediato ao usuário; o backend valida tudo de novo.
export const ticketFields = {
  title: z
    .string()
    .trim()
    .min(5, "O título precisa ter pelo menos 5 caracteres.")
    .max(150, "O título pode ter no máximo 150 caracteres."),
  description: z
    .string()
    .trim()
    .min(10, "Descreva o problema com pelo menos 10 caracteres.")
    .max(5000, "A descrição pode ter no máximo 5000 caracteres."),
  category: z.coerce.number<string>({ error: "Escolha uma categoria." }).int().positive("Escolha uma categoria."),
  priority: z.coerce.number<string>().int().min(1).max(4),
};

export const newTicketSchema = z.object(ticketFields);
export type NewTicketForm = z.input<typeof newTicketSchema>;
export type NewTicketData = z.output<typeof newTicketSchema>;
