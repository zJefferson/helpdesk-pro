import { Route, Routes } from "react-router-dom";
import { RequireAuth } from "./auth/RequireAuth";
import { LoginPage } from "./pages/LoginPage";

function Placeholder() {
  return <p className="p-8">Login OK — próximas telas em construção.</p>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route path="*" element={<Placeholder />} />
      </Route>
    </Routes>
  );
}
