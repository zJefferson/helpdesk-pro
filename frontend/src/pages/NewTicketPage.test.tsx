import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { fakeUsers, loginAs, renderPage } from "../test/render";
import { server } from "../test/server";
import { NewTicketPage } from "./NewTicketPage";

function mockCategories() {
  server.use(
    http.get("/api/v1/categories/", () =>
      HttpResponse.json([
        { id: 1, name: "Hardware", description: "", is_active: true },
        { id: 2, name: "Rede", description: "", is_active: true },
      ]),
    ),
  );
}

async function fillValidForm() {
  await userEvent.type(await screen.findByLabelText("Título"), "Monitor piscando");
  await userEvent.selectOptions(screen.getByLabelText("Categoria"), "2");
  await userEvent.selectOptions(screen.getByLabelText("Prioridade"), "3");
  await userEvent.type(screen.getByLabelText("Descrição"), "O monitor pisca a cada minuto.");
}

describe("NewTicketPage", () => {
  it("valida os campos no navegador sem chamar a API", async () => {
    loginAs(fakeUsers.REQUESTER);
    mockCategories();
    let posted = false;
    server.use(
      http.post("/api/v1/tickets/", () => {
        posted = true;
        return HttpResponse.json({});
      }),
    );
    renderPage(<NewTicketPage />);

    await userEvent.type(await screen.findByLabelText("Título"), "Oi");
    await userEvent.click(screen.getByRole("button", { name: "Abrir chamado" }));

    expect(await screen.findByText("O título precisa ter pelo menos 5 caracteres.")).toBeInTheDocument();
    expect(screen.getByText("Escolha uma categoria.")).toBeInTheDocument();
    expect(posted).toBe(false);
  });

  it("envia os dados convertidos para a API", async () => {
    loginAs(fakeUsers.REQUESTER);
    mockCategories();
    let body: unknown;
    server.use(
      http.post("/api/v1/tickets/", async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ id: 42 }, { status: 201 });
      }),
    );
    renderPage(<NewTicketPage />);

    await fillValidForm();
    await userEvent.click(screen.getByRole("button", { name: "Abrir chamado" }));

    expect(await screen.findByText("Chamado #42 aberto com sucesso.")).toBeInTheDocument();
    expect(body).toEqual({
      title: "Monitor piscando",
      description: "O monitor pisca a cada minuto.",
      category: 2,
      priority: 3,
    });
  });

  it("mostra no campo certo o erro de validação devolvido pelo backend", async () => {
    loginAs(fakeUsers.REQUESTER);
    mockCategories();
    server.use(
      http.post("/api/v1/tickets/", () =>
        HttpResponse.json({ category: ["Esta categoria está inativa."] }, { status: 400 }),
      ),
    );
    renderPage(<NewTicketPage />);

    await fillValidForm();
    await userEvent.click(screen.getByRole("button", { name: "Abrir chamado" }));

    const field = await screen.findByLabelText("Categoria");
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(screen.getAllByText("Esta categoria está inativa.").length).toBeGreaterThan(0);
  });
});
