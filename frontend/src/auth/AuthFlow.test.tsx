import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { api } from "../api/client";
import { AppLayout } from "../components/AppLayout";
import { ToastProvider } from "../components/Toaster";
import { LoginPage } from "../pages/LoginPage";
import { fakeUsers, loginAs } from "../test/render";
import { server } from "../test/server";
import { AuthProvider } from "./AuthContext";
import { RequireAuth } from "./RequireAuth";

function WhereAmI() {
  return <p>Página: {useLocation().pathname}</p>;
}

function renderApp(route: string) {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={[route]}>
        <ToastProvider>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route element={<RequireAuth />}>
                <Route element={<AppLayout />}>
                  <Route path="*" element={<WhereAmI />} />
                </Route>
              </Route>
            </Routes>
          </AuthProvider>
        </ToastProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function allowLoginAs(user: (typeof fakeUsers)[keyof typeof fakeUsers]) {
  server.use(
    http.post("/api/v1/auth/session/login/", () => HttpResponse.json({ access: "novo" })),
    http.post("/api/v1/auth/session/logout/", () => new HttpResponse(null, { status: 204 })),
    http.get("/api/v1/auth/me/", () => HttpResponse.json(user)),
  );
}

async function loginThroughForm() {
  await userEvent.type(await screen.findByLabelText("E-mail"), "outra@example.com");
  await userEvent.type(screen.getByLabelText("Senha"), "qualquer");
  await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
}

describe("fluxo de sessão", () => {
  it("após logout voluntário, o próximo login começa no dashboard (não na última página)", async () => {
    loginAs(fakeUsers.ADMIN);
    allowLoginAs(fakeUsers.REQUESTER);
    renderApp("/tickets/42");
    expect(await screen.findByText("Página: /tickets/42")).toBeInTheDocument();

    await userEvent.click(screen.getAllByRole("button", { name: "Sair" })[0]!);
    await loginThroughForm();

    expect(await screen.findByText("Página: /")).toBeInTheDocument();
  });

  it("quando a sessão expira, o login devolve o usuário à página onde estava", async () => {
    loginAs(fakeUsers.ADMIN);
    renderApp("/tickets/42");
    expect(await screen.findByText("Página: /tickets/42")).toBeInTheDocument();

    // A API passa a recusar o token e a renovação falha (sessão expirada).
    server.use(
      http.get("/api/v1/tickets/", () => new HttpResponse(null, { status: 401 })),
      http.post("/api/v1/auth/session/refresh/", () => new HttpResponse(null, { status: 401 })),
    );
    await api("/api/v1/tickets/").catch(() => undefined);

    allowLoginAs(fakeUsers.ADMIN);
    await loginThroughForm();

    expect(await screen.findByText("Página: /tickets/42")).toBeInTheDocument();
  });
});
