import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import type { Paginated, Ticket } from "../api/types";
import { fakeUsers, loginAs, renderPage } from "../test/render";
import { server } from "../test/server";
import { TicketListPage } from "./TicketListPage";

function makeTicket(id: number, overrides: Partial<Ticket> = {}): Ticket {
  return {
    id,
    title: `Chamado ${id}`,
    description: "Descrição de teste.",
    category: 1,
    category_name: "Rede",
    priority: 2,
    status: "OPEN",
    requester: { id: 2, full_name: "Sara Solicitante", email: "sara@example.com" },
    assignee: null,
    created_at: "2026-10-08T10:00:00Z",
    updated_at: "2026-10-08T10:00:00Z",
    resolved_at: null,
    closed_at: null,
    permissions: {
      editable_fields: [],
      status_transitions: [],
      can_assign: false,
      can_take: false,
      can_comment: true,
      can_comment_internal: false,
    },
    ...overrides,
  };
}

/** API falsa: devolve 45 chamados paginados e registra as URLs pedidas. */
function mockTicketsApi() {
  const requested: URL[] = [];
  const all = Array.from({ length: 45 }, (_, i) => makeTicket(45 - i));
  server.use(
    http.get("/api/v1/categories/", () =>
      HttpResponse.json([{ id: 1, name: "Rede", description: "", is_active: true }]),
    ),
    http.get("/api/v1/users/technicians/", () => HttpResponse.json([])),
    http.get("/api/v1/tickets/", ({ request }) => {
      const url = new URL(request.url);
      requested.push(url);
      const page = Number(url.searchParams.get("page") ?? 1);
      const search = url.searchParams.get("search");
      const items = search ? all.filter((t) => t.title.includes(search)) : all;
      const body: Paginated<Ticket> = {
        count: items.length,
        next: page * 20 < items.length ? `?page=${page + 1}` : null,
        previous: page > 1 ? `?page=${page - 1}` : null,
        results: items.slice((page - 1) * 20, page * 20),
      };
      return HttpResponse.json(body);
    }),
  );
  return requested;
}

describe("TicketListPage", () => {
  it("lista e pagina os chamados", async () => {
    loginAs(fakeUsers.ADMIN);
    const requested = mockTicketsApi();
    renderPage(<TicketListPage />, { path: "/tickets", route: "/tickets" });

    expect(await screen.findByText("1–20 de 45")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Página anterior" })).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: "Próxima página" }));

    expect(await screen.findByText("21–40 de 45")).toBeInTheDocument();
    expect(requested.at(-1)!.searchParams.get("page")).toBe("2");
  });

  it("envia filtros de status e prioridade para a API e volta à página 1", async () => {
    loginAs(fakeUsers.ADMIN);
    const requested = mockTicketsApi();
    renderPage(<TicketListPage />, { path: "/tickets", route: "/tickets?page=2" });
    await screen.findByText("21–40 de 45");

    await userEvent.selectOptions(screen.getByLabelText("Filtrar por status"), "active");
    await userEvent.selectOptions(screen.getByLabelText("Filtrar por prioridade"), "4");

    await waitFor(() => {
      const last = requested.at(-1)!.searchParams;
      expect(last.getAll("status")).toEqual(["OPEN", "IN_PROGRESS", "WAITING_REQUESTER"]);
      expect(last.get("priority")).toBe("4");
      expect(last.get("page")).toBe("1");
    });
  });

  it("busca com atraso (uma requisição, não uma por tecla)", async () => {
    loginAs(fakeUsers.ADMIN);
    const requested = mockTicketsApi();
    renderPage(<TicketListPage />, { path: "/tickets", route: "/tickets" });
    await screen.findByText("1–20 de 45");
    const before = requested.length;

    await userEvent.type(screen.getByLabelText("Buscar chamados"), "Chamado 4");

    expect(await screen.findByText("1–7 de 7")).toBeInTheDocument(); // 4 e 40..45
    const searches = requested.slice(before).filter((u) => u.searchParams.has("search"));
    expect(searches.length).toBe(1);
  });

  it("mostra estado vazio com orientação", async () => {
    loginAs(fakeUsers.REQUESTER);
    mockTicketsApi();
    server.use(
      http.get("/api/v1/tickets/", () =>
        HttpResponse.json({ count: 0, next: null, previous: null, results: [] }),
      ),
    );
    renderPage(<TicketListPage />, { path: "/tickets", route: "/tickets?search=xyz" });

    expect(await screen.findByText("Nenhum chamado encontrado")).toBeInTheDocument();
  });

  it("solicitante não vê o filtro de responsável nem chama a lista de técnicos", async () => {
    loginAs(fakeUsers.REQUESTER);
    let technicianCalls = 0;
    mockTicketsApi();
    server.use(
      http.get("/api/v1/users/technicians/", () => {
        technicianCalls++;
        return new HttpResponse(null, { status: 403 });
      }),
    );
    renderPage(<TicketListPage />, { path: "/tickets", route: "/tickets" });

    expect(await screen.findByRole("heading", { name: "Meus chamados" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Filtrar por responsável")).not.toBeInTheDocument();
    expect(technicianCalls).toBe(0);
  });
});

describe("TicketListPage — página que deixou de existir", () => {
  it("volta para a página 1 quando a API responde 404 para a página pedida", async () => {
    loginAs(fakeUsers.ADMIN);
    const requested = mockTicketsApi();
    server.use(
      http.get("/api/v1/tickets/", ({ request }) => {
        const url = new URL(request.url);
        requested.push(url);
        if (url.searchParams.get("page") === "3") {
          return HttpResponse.json({ detail: "Página inválida." }, { status: 404 });
        }
        return HttpResponse.json({ count: 1, next: null, previous: null, results: [makeTicket(1)] });
      }),
    );
    renderPage(<TicketListPage />, { path: "/tickets", route: "/tickets?page=3" });

    expect(await screen.findByText("1–1 de 1")).toBeInTheDocument();
    expect(requested.at(-1)!.searchParams.get("page")).toBe("1");
  });
});
