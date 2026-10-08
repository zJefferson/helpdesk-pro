import { setupServer } from "msw/node";

/** Servidor falso da API para os testes (MSW). Cada teste registra seus próprios handlers. */
export const server = setupServer();
