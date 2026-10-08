import { http, HttpResponse } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";
import { server } from "../test/server";
import { ApiError, api, buildUrl, setAccessToken, setSessionExpiredHandler } from "./client";

afterEach(() => {
  setAccessToken(null);
  setSessionExpiredHandler(null);
});

describe("buildUrl", () => {
  it("ignora valores vazios e repete parâmetros de lista", () => {
    expect(buildUrl("/x/", { a: 1, b: "", c: undefined, s: ["OPEN", "CLOSED"] })).toBe(
      "/x/?a=1&s=OPEN&s=CLOSED",
    );
  });
});

describe("api", () => {
  it("envia o access token em memória no cabeçalho Authorization", async () => {
    let header: string | null = null;
    server.use(
      http.get("/api/v1/auth/me/", ({ request }) => {
        header = request.headers.get("Authorization");
        return HttpResponse.json({ id: 1 });
      }),
    );
    setAccessToken("abc");

    await api("/api/v1/auth/me/");

    expect(header).toBe("Bearer abc");
  });

  it("renova o token UMA vez para várias requisições simultâneas com 401", async () => {
    let refreshCalls = 0;
    server.use(
      http.post("/api/v1/auth/session/refresh/", () => {
        refreshCalls++;
        return HttpResponse.json({ access: "novo" });
      }),
      http.get("/api/v1/tickets/", ({ request }) =>
        request.headers.get("Authorization") === "Bearer novo"
          ? HttpResponse.json({ ok: true })
          : new HttpResponse(null, { status: 401 }),
      ),
    );
    setAccessToken("expirado");

    const results = await Promise.all([api("/api/v1/tickets/"), api("/api/v1/tickets/")]);

    expect(results).toEqual([{ ok: true }, { ok: true }]);
    expect(refreshCalls).toBe(1);
  });

  it("avisa a aplicação quando a sessão não pode ser renovada", async () => {
    const onExpired = vi.fn();
    setSessionExpiredHandler(onExpired);
    server.use(
      http.post("/api/v1/auth/session/refresh/", () => new HttpResponse(null, { status: 401 })),
      http.get("/api/v1/tickets/", () => new HttpResponse(null, { status: 401 })),
    );

    await expect(api("/api/v1/tickets/")).rejects.toMatchObject({ status: 401 });
    expect(onExpired).toHaveBeenCalledOnce();
  });

  it("converte erros de validação em mensagens por campo", async () => {
    server.use(
      http.post("/api/v1/tickets/", () =>
        HttpResponse.json({ title: ["Muito curto."], category: ["Inativa."] }, { status: 400 }),
      ),
    );

    const error = (await api("/api/v1/tickets/", { method: "POST", body: {} }).catch(
      (e: unknown) => e,
    )) as ApiError;

    expect(error).toBeInstanceOf(ApiError);
    expect(error.fieldErrors).toEqual({ title: "Muito curto.", category: "Inativa." });
  });

  it("usa a mensagem 'detail' do backend e um texto padrão para 403 sem detalhe", async () => {
    server.use(
      http.get("/api/v1/a/", () => HttpResponse.json({ detail: "Sem permissão X." }, { status: 403 })),
      http.get("/api/v1/b/", () => new HttpResponse(null, { status: 403 })),
    );

    await expect(api("/api/v1/a/")).rejects.toThrow("Sem permissão X.");
    await expect(api("/api/v1/b/")).rejects.toThrow("Você não tem permissão");
  });

  it("transforma falha de rede em ApiError com status 0", async () => {
    server.use(http.get("/api/v1/x/", () => HttpResponse.error()));

    await expect(api("/api/v1/x/")).rejects.toMatchObject({ status: 0 });
  });
});
