import { Link, Route, Routes } from "react-router-dom";
import { RequireAuth } from "./auth/RequireAuth";
import { AppLayout } from "./components/AppLayout";
import { EmptyState } from "./components/ui";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";

function NotFoundPage() {
  return (
    <EmptyState
      title="Página não encontrada"
      description="O endereço acessado não existe."
      action={
        <Link to="/" className="text-sm font-semibold text-indigo-600 hover:text-indigo-500">
          Voltar ao início
        </Link>
      }
    />
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
