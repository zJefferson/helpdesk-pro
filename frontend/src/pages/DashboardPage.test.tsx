import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { DashboardSummary } from "../api/types";
import { fakeUsers, loginAs, renderPage } from "../test/render";
import { server } from "../test/server";
import { DashboardPage } from "./DashboardPage";

const summary: DashboardSummary = {
  total: 9,
  open: 5,
  unassigned: 2,
  assigned_to_me: 3,
  resolved_last_30_days: 4,
  avg_resolution_hours: 26.5,
  by_status: [
    { status: "OPEN", label: "Aberto", count: 2 },
    { status: "IN_PROGRESS", label: "Em atendimento", count: 2 },
    { status: "WAITING_REQUESTER", label: "Aguardando solicitante", count: 1 },
    { status: "RESOLVED", label: "Resolvido", count: 3 },
    { status: "CLOSED", label: "Fechado", count: 1 },
    { status: "CANCELLED", label: "Cancelado", count: 0 },
  ],
  by_priority: [
    { priority: 1, label: "Baixa", count: 1 },
    { priority: 2, label: "Média", count: 4 },
    { priority: 3, label: "Alta", count: 3 },
    { priority: 4, label: "Crítica", count: 1 },
  ],
  open_by_category: [{ id: 1, name: "Rede", count: 5 }],
};

function card(label: string) {
  return screen.getByText(label).closest("div.rounded-lg") as HTMLElement;
}

describe("DashboardPage", () => {
  it("mostra os indicadores vindos da API para o técnico", async () => {
    loginAs(fakeUsers.TECHNICIAN);
    server.use(http.get("/api/v1/dashboard/summary/", () => HttpResponse.json(summary)));
    renderPage(<DashboardPage />);

    expect(await screen.findByText("Olá, Tiago")).toBeInTheDocument();
    await screen.findByText("Chamados ativos"); // aguarda os dados da API
    expect(within(card("Chamados ativos")).getByText("5")).toBeInTheDocument();
    expect(within(card("Sem responsável")).getByText("2")).toBeInTheDocument();
    expect(within(card("Atribuídos a mim")).getByText("3")).toBeInTheDocument();
    expect(within(card("Tempo médio de resolução")).getByText("26,5 h")).toBeInTheDocument();
  });

  it("adapta os cartões para o solicitante", async () => {
    loginAs(fakeUsers.REQUESTER);
    server.use(http.get("/api/v1/dashboard/summary/", () => HttpResponse.json(summary)));
    renderPage(<DashboardPage />);

    expect(await screen.findByText("Meus chamados ativos")).toBeInTheDocument();
    expect(within(card("Aguardando sua resposta")).getByText("1")).toBeInTheDocument();
    expect(screen.queryByText("Sem responsável")).not.toBeInTheDocument();
  });

  it("mostra erro com opção de tentar de novo", async () => {
    loginAs(fakeUsers.ADMIN);
    server.use(
      http.get("/api/v1/dashboard/summary/", () => new HttpResponse(null, { status: 500 })),
    );
    renderPage(<DashboardPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("erro inesperado");
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });
});
