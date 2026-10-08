/**
 * Cliente HTTP central: TODA chamada à API passa por aqui.
 *
 * Responsabilidades:
 * 1. Anexar o access token (guardado só EM MEMÓRIA, nunca em localStorage).
 * 2. Ao receber 401, renovar o access usando o cookie HttpOnly e repetir a requisição uma vez.
 * 3. Se a renovação falhar, avisar a aplicação (logout) via `setSessionExpiredHandler`.
 * 4. Converter respostas de erro em `ApiError`, com mensagens prontas para a interface.
 */

const SESSION_REFRESH_URL = "/api/v1/auth/session/refresh/";

let accessToken: string | null = null;
let onSessionExpired: (() => void) | null = null;
let refreshInFlight: Promise<boolean> | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function setSessionExpiredHandler(handler: (() => void) | null) {
  onSessionExpired = handler;
}

type ErrorBody = { detail?: string } & Record<string, unknown>;

export class ApiError extends Error {
  readonly status: number;
  readonly body: ErrorBody | null;

  constructor(status: number, body: ErrorBody | null, message?: string) {
    super(message ?? describeError(status, body));
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }

  /** Erros de validação por campo: { title: ["Mensagem"] } → { title: "Mensagem" }. */
  get fieldErrors(): Record<string, string> {
    if (!this.body || this.status !== 400) return {};
    const result: Record<string, string> = {};
    for (const [field, value] of Object.entries(this.body)) {
      if (field === "detail") continue;
      result[field] = Array.isArray(value) ? String(value[0]) : String(value);
    }
    return result;
  }
}

function describeError(status: number, body: ErrorBody | null): string {
  if (body?.detail) return body.detail;
  if (status === 400 && body) {
    const first = Object.values(body)[0];
    if (first) return Array.isArray(first) ? String(first[0]) : String(first);
  }
  switch (status) {
    case 0:
      return "Não foi possível conectar ao servidor. Verifique sua conexão.";
    case 401:
      return "Sua sessão expirou. Faça login novamente.";
    case 403:
      return "Você não tem permissão para realizar esta ação.";
    case 404:
      return "Registro não encontrado.";
    case 429:
      return "Muitas tentativas. Aguarde um pouco e tente de novo.";
    default:
      return "Ocorreu um erro inesperado. Tente novamente.";
  }
}

/**
 * Renova o access token usando o cookie HttpOnly (o JavaScript nunca vê o refresh).
 * Se várias requisições receberem 401 ao mesmo tempo, todas aguardam UMA única renovação.
 */
export function refreshAccessToken(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = fetch(SESSION_REFRESH_URL, { method: "POST", credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) {
          accessToken = null;
          return false;
        }
        const data = (await response.json()) as { access: string };
        accessToken = data.access;
        return true;
      })
      .catch(() => false)
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

export type QueryParams = Record<
  string,
  string | number | boolean | null | undefined | Array<string | number>
>;

export function buildUrl(path: string, params?: QueryParams): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) value.forEach((v) => search.append(key, String(v)));
    else search.append(key, String(value));
  }
  const query = search.toString();
  return query ? `${path}?${query}` : path;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH";
  body?: unknown;
  params?: QueryParams;
  /** false = não tenta renovar a sessão ao receber 401 (ex.: tela de login). */
  retryOn401?: boolean;
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, params, retryOn401 = true } = options;
  const url = buildUrl(path, params);

  const send = () =>
    fetch(url, {
      method,
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

  let response: Response;
  try {
    response = await send();
    if (response.status === 401 && retryOn401) {
      if (await refreshAccessToken()) {
        response = await send();
      } else {
        onSessionExpired?.();
      }
    }
  } catch {
    throw new ApiError(0, null);
  }

  if (response.status === 204) return undefined as T;

  const data = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, data as ErrorBody | null);
  return data as T;
}

/** Mensagem amigável para qualquer erro (usado em toasts e estados de erro). */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Ocorreu um erro inesperado. Tente novamente.";
}
