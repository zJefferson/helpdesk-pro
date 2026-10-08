import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { User } from "../api/types";
import { AuthProvider } from "../auth/AuthContext";
import { RequireAuth } from "../auth/RequireAuth";
import { ToastProvider } from "../components/Toaster";
import { server } from "./server";

export const fakeUsers: Record<User["role"], User> = {
  REQUESTER: {
    id: 2,
    email: "sara@example.com",
    first_name: "Sara",
    last_name: "Solicitante",
    role: "REQUESTER",
    is_active: true,
    date_joined: "2026-10-01T10:00:00Z",
  },
  TECHNICIAN: {
    id: 3,
    email: "tiago@example.com",
    first_name: "Tiago",
    last_name: "Técnico",
    role: "TECHNICIAN",
    is_active: true,
    date_joined: "2026-10-01T10:00:00Z",
  },
  ADMIN: {
    id: 1,
    email: "ana@example.com",
    first_name: "Ana",
    last_name: "Admin",
    role: "ADMIN",
    is_active: true,
    date_joined: "2026-10-01T10:00:00Z",
  },
};

/** Simula uma sessão já existente (cookie válido) para o usuário informado. */
export function loginAs(user: User | null) {
  server.use(
    http.post("/api/v1/auth/session/refresh/", () =>
      user ? HttpResponse.json({ access: "token-teste" }) : new HttpResponse(null, { status: 401 }),
    ),
    http.get("/api/v1/auth/me/", () => HttpResponse.json(user)),
  );
}

/** Renderiza uma tela com todos os providers do app, em uma rota protegida. */
export function renderPage(ui: ReactElement, { path = "/", route = "/" } = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <ToastProvider>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<p>Tela de login</p>} />
              <Route element={<RequireAuth />}>
                <Route path={path} element={ui} />
              </Route>
            </Routes>
          </AuthProvider>
        </ToastProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
