import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../store/authStore";

export function ProtectedRoute() {
  const status = useAuthStore((s) => s.status);

  if (status === "idle" || status === "loading") {
    return <p className="page-loading">carregando…</p>;
  }
  if (status !== "authenticated") {
    return <Navigate to="/entrar" replace />;
  }
  return <Outlet />;
}
