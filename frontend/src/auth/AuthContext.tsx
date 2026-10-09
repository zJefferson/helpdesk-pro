import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { refreshAccessToken, setAccessToken, setSessionExpiredHandler } from "../api/client";
import { authApi } from "../api/endpoints";
import type { User } from "../api/types";

/**
 * Estado de autenticação da aplicação.
 *
 * - O access token fica só em memória (dentro de api/client.ts).
 * - Ao abrir/recarregar a página, tentamos renovar a sessão pelo cookie HttpOnly.
 * - O usuário (e o perfil) vem SEMPRE de /auth/me/. O perfil aqui serve apenas para
 *   decidir o que MOSTRAR; quem decide o que é PERMITIDO é o backend.
 */

/** Por que não há sessão: decide se o login deve devolver o usuário à página anterior. */
type AnonymousReason = "initial" | "expired" | "logout";

type AuthState =
  | { status: "loading"; user: null }
  | { status: "anonymous"; user: null; reason: AnonymousReason }
  | { status: "authenticated"; user: User };

interface AuthContextValue {
  state: AuthState;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "loading", user: null });
  const queryClient = useQueryClient();

  const endSession = useCallback(
    (reason: AnonymousReason) => {
      setAccessToken(null);
      queryClient.clear(); // remove dados do usuário anterior do cache
      setState({ status: "anonymous", user: null, reason });
    },
    [queryClient],
  );

  // Restaura a sessão ao carregar a página (o cookie HttpOnly sobrevive ao F5).
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const ok = await refreshAccessToken();
      if (!ok) {
        if (!cancelled) setState({ status: "anonymous", user: null, reason: "initial" });
        return;
      }
      try {
        const user = await authApi.me();
        if (!cancelled) setState({ status: "authenticated", user });
      } catch {
        if (!cancelled) setState({ status: "anonymous", user: null, reason: "initial" });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Se a sessão expirar no meio do uso, o cliente HTTP avisa e voltamos ao login.
  useEffect(() => {
    setSessionExpiredHandler(() => endSession("expired"));
    return () => setSessionExpiredHandler(null);
  }, [endSession]);

  const login = useCallback(async (email: string, password: string) => {
    const { access } = await authApi.login(email, password);
    setAccessToken(access);
    const user = await authApi.me();
    setState({ status: "authenticated", user });
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      endSession("logout");
    }
  }, [endSession]);

  const value = useMemo(() => ({ state, login, logout }), [state, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth precisa estar dentro de <AuthProvider>");
  return context;
}

/** Usuário logado (use apenas dentro de rotas protegidas). */
export function useCurrentUser(): User {
  const { state } = useAuth();
  if (state.status !== "authenticated") throw new Error("Nenhum usuário autenticado");
  return state.user;
}
