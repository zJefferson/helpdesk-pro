import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import { RequireAuth } from "../auth/RequireAuth";
import { ToastProvider } from "../components/Toaster";
import { fakeUsers, loginAs } from "../test/render";
import { server } from "../test/server";
import { LoginPage } from "./LoginPage";

function renderApp(route = "/login") {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={[route]}>
        <ToastProvider>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route element={<RequireAuth />}>
                <Route path="/" element={<p>Área logada</p>} />
              </Route>
            </Routes>
          </AuthProvider>
        </ToastProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("LoginPage", () => {
  it("valida os campos antes de chamar a API", async () => {
    loginAs(null);
    renderApp();

    await userEvent.click(await screen.findByRole("button", { name: "Entrar" }));

    expect(await screen.findByText("Informe seu e-mail.")).toBeInTheDocument();
    expect(screen.getByText("Informe sua senha.")).toBeInTheDocument();
  });

  it("mostra o erro do backend quando as credenciais são inválidas", async () => {
    loginAs(null);
    server.use(
      http.post("/api/v1/auth/session/login/", () =>
        HttpResponse.json({ detail: "E-mail ou senha inválidos." }, { status: 401 }),
      ),
    );
    renderApp();

    await userEvent.type(await screen.findByLabelText("E-mail"), "x@example.com");
    await userEvent.type(screen.getByLabelText("Senha"), "errada");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("E-mail ou senha inválidos.");
  });

  it("entra e redireciona para a área logada", async () => {
    loginAs(null);
    server.use(
      http.post("/api/v1/auth/session/login/", () => HttpResponse.json({ access: "abc" })),
      http.get("/api/v1/auth/me/", () => HttpResponse.json(fakeUsers.REQUESTER)),
    );
    renderApp();

    await userEvent.type(await screen.findByLabelText("E-mail"), "sara@example.com");
    await userEvent.type(screen.getByLabelText("Senha"), "certa");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByText("Área logada")).toBeInTheDocument();
  });

  it("rota protegida sem sessão redireciona para o login", async () => {
    loginAs(null);
    renderApp("/");

    expect(await screen.findByRole("heading", { name: "Entre na sua conta" })).toBeInTheDocument();
  });

  it("sessão existente (cookie) restaura o usuário sem pedir login", async () => {
    loginAs(fakeUsers.ADMIN);
    renderApp("/");

    expect(await screen.findByText("Área logada")).toBeInTheDocument();
  });
});
