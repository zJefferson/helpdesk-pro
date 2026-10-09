import { useMutation, useQueryClient } from "@tanstack/react-query";
import { errorMessage } from "../../api/client";
import type { Ticket } from "../../api/types";
import { useToast } from "../../components/Toaster";

/**
 * Padrão de todas as ações do chamado (editar, atribuir, mudar status):
 * - sucesso: atualiza o chamado na tela, recarrega histórico/lista/dashboard e mostra toast;
 * - erro: mostra o motivo vindo do backend e recarrega o chamado (as permissões podem ter mudado).
 */
export function useTicketMutation<TVariables>(
  ticketId: number,
  mutationFn: (variables: TVariables) => Promise<Ticket>,
  successMessage: string,
) {
  const queryClient = useQueryClient();
  const toast = useToast();

  return useMutation({
    mutationFn,
    onSuccess: (ticket) => {
      queryClient.setQueryData(["ticket", ticketId], ticket);
      void queryClient.invalidateQueries({ queryKey: ["ticket", ticketId, "history"] });
      void queryClient.invalidateQueries({ queryKey: ["tickets"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(successMessage);
    },
    onError: (error) => {
      toast.error(errorMessage(error));
      void queryClient.invalidateQueries({ queryKey: ["ticket", ticketId] });
    },
  });
}
