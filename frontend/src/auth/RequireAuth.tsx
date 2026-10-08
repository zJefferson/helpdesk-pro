import { Navigate, Outlet, useLocation } from "react-router-dom";
import { LoadingState } from "../components/ui";
import { useAuth } from "./AuthContext";

/** Protege as rotas internas: sem sessão, redireciona para o login (e volta depois). */
export function RequireAuth() {
  const { state } = useAuth();
  const location = useLocation();

  if (state.status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingState label="Verificando sessão..." />
      </div>
    );
  }
  if (state.status === "anonymous") {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <Outlet />;
}
