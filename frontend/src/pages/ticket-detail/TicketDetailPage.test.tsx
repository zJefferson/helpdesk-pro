import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { Ticket, TicketPermissions } from "../../api/types";
import { fakeUsers, loginAs, renderPage } from "../../test/render";
import { server } from "../../test/server";
import { TicketDetailPage } from "./TicketDetailPage";

const NO_PERMISSIONS: TicketPermissions = {
  editable_fields: [],
  status_transitions: [],
  can_assign: false,
  can_take: false,
  can_comment: true,
  can_comment_internal: false,
};

function ticket(overrides: Partial<Ticket> = {}): Ticket {
  return {
    id: 7,
    title: "VPN caindo",
    description: "A VPN cai a cada 5 minutos.",
    category: 1,
    category_name: "Rede",
    priority: 3,
    status: "OPEN",
    requester: { id: 2, full_name: "Sara Solicitante", email: "sara@example.com" },
    assignee: null,
    created_at: "2026-10-08T10:00:00Z",
    updated_at: "2026-10-08T10:00:00Z",
    resolved_at: null,
    closed_at: null,
    permissions: NO_PERMISSIONS,
    ...overrides,
  };
}

function mockApi(data: Ticket) {
  const calls: Array<{ url: string; body: unknown }> = [];
  server.use(
    http.get("/api/v1/tickets/7/", () => HttpResponse.json(data)),
    http.get("/api/v1/tickets/7/comments/", () => HttpResponse.json([])),
    http.get("/api/v1/tickets/7/history/", () => HttpResponse.json([])),
    http.get("/api/v1/categories/", () => HttpResponse.json([])),
    http.get("/api/v1/users/technicians/", () =>
      HttpResponse.json([{ id: 3, full_name: "Tiago Técnico", email: "t@example.com" }]),
    ),
    http.post("/api/v1/tickets/7/:action/", async ({ request, params }) => {
      calls.push({ url: String(params.action), body: await request.json() });
      return HttpResponse.json(data);
    }),
  );
  return calls;
}

function renderDetail() {
  renderPage(<TicketDetailPage />, { path: "/tickets/:id", route: "/tickets/7" });
}

describe("TicketDetailPage", () => {
  it("solicitante vê só as ações que o backend permite e não vê nota interna", async () => {
    loginAs(fakeUsers.REQUESTER);
    mockApi(
      ticket({
        permissions: { ...NO_PERMISSIONS, editable_fields: ["title"], status_transitions: ["CANCELLED"] },
      }),
    );
    renderDetail();

    expect(await screen.findByRole("heading", { name: "VPN caindo" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancelar chamado" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Editar" })).toBeInTheDocument();
    expect(screen.queryByLabelText(/Atribuir/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Nota interna/)).not.toBeInTheDocument();
  });

  it("cancelar pede confirmação antes de chamar a API", async () => {
    loginAs(fakeUsers.REQUESTER);
    const calls = mockApi(ticket({ permissions: { ...NO_PERMISSIONS, status_transitions: ["CANCELLED"] } }));
    renderDetail();

    await userEvent.click(await screen.findByRole("button", { name: "Cancelar chamado" }));
    expect(calls).toHaveLength(0);

    await userEvent.click(screen.getByRole("button", { name: "Confirmar: cancelado?" }));
    expect(await screen.findByText("Status atualizado.")).toBeInTheDocument();
    expect(calls).toEqual([{ url: "status", body: { status: "CANCELLED" } }]);
  });

  it("reabrir tem rótulo próprio (não 'Iniciar atendimento')", async () => {
    loginAs(fakeUsers.REQUESTER);
    mockApi(
      ticket({
        status: "RESOLVED",
        permissions: { ...NO_PERMISSIONS, status_transitions: ["CLOSED", "IN_PROGRESS"] },
      }),
    );
    renderDetail();

    expect(await screen.findByRole("button", { name: "Confirmar solução" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reabrir (não foi resolvido)" })).toBeInTheDocument();
  });

  it("técnico pode assumir chamado sem responsável", async () => {
    loginAs(fakeUsers.TECHNICIAN);
    const calls = mockApi(
      ticket({ permissions: { ...NO_PERMISSIONS, can_take: true, can_comment_internal: true } }),
    );
    renderDetail();

    await userEvent.click(await screen.findByRole("button", { name: "Assumir chamado" }));

    expect(await screen.findByText("Responsável atualizado.")).toBeInTheDocument();
    expect(calls).toEqual([{ url: "assign", body: { assignee_id: fakeUsers.TECHNICIAN.id } }]);
    expect(screen.getByLabelText(/Nota interna/)).toBeInTheDocument();
  });

  it("admin atribui escolhendo um técnico", async () => {
    loginAs(fakeUsers.ADMIN);
    const calls = mockApi(ticket({ permissions: { ...NO_PERMISSIONS, can_assign: true } }));
    renderDetail();

    const select = await screen.findByLabelText("Atribuir para");
    await screen.findByRole("option", { name: "Tiago Técnico" });
    await userEvent.selectOptions(select, "3");
    await userEvent.click(screen.getByRole("button", { name: "Atribuir" }));

    expect(await screen.findByText("Responsável atualizado.")).toBeInTheDocument();
    expect(calls).toEqual([{ url: "assign", body: { assignee_id: 3 } }]);
  });

  it("mostra o erro do backend quando a ação é recusada", async () => {
    loginAs(fakeUsers.TECHNICIAN);
    mockApi(ticket({ permissions: { ...NO_PERMISSIONS, can_take: true } }));
    server.use(
      http.post("/api/v1/tickets/7/assign/", () =>
        HttpResponse.json({ detail: "Este chamado já tem um responsável." }, { status: 403 }),
      ),
    );
    renderDetail();

    await userEvent.click(await screen.findByRole("button", { name: "Assumir chamado" }));

    expect(await screen.findByText("Este chamado já tem um responsável.")).toBeInTheDocument();
  });

  it("chamado encerrado não mostra ações nem formulário de comentário", async () => {
    loginAs(fakeUsers.ADMIN);
    mockApi(ticket({ status: "CLOSED", permissions: { ...NO_PERMISSIONS, can_comment: false } }));
    renderDetail();

    expect(await screen.findByText(/não aceita novos comentários/)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Ações" })).not.toBeInTheDocument();
  });

  it("404 da API mostra 'Chamado não encontrado'", async () => {
    loginAs(fakeUsers.REQUESTER);
    server.use(
      http.get("/api/v1/tickets/7/", () => HttpResponse.json({ detail: "Não encontrado." }, { status: 404 })),
    );
    renderDetail();

    expect(await screen.findByText("Chamado não encontrado")).toBeInTheDocument();
  });

  it("mostra comentários e diferencia notas internas", async () => {
    loginAs(fakeUsers.TECHNICIAN);
    mockApi(ticket());
    server.use(
      http.get("/api/v1/tickets/7/comments/", () =>
        HttpResponse.json([
          {
            id: 1,
            author: { id: 3, full_name: "Tiago Técnico", email: "t@example.com" },
            body: "Certificado expirado.",
            is_internal: true,
            created_at: "2026-10-08T10:05:00Z",
          },
        ]),
      ),
    );
    renderDetail();

    const item = (await screen.findByText("Certificado expirado.")).closest("li")!;
    expect(within(item).getByText("Nota interna")).toBeInTheDocument();
  });
});
