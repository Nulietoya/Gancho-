import { NavLink, Outlet } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import { OfflineBanner } from "./OfflineBanner";

export function Layout() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  return (
    <div className="app-shell">
      <OfflineBanner />
      <header className="app-header">
        <span className="app-name">Gancho</span>
        <nav className="app-nav">
          <NavLink to="/" end>
            Hoje
          </NavLink>
          <NavLink to="/checkin">Check-in</NavLink>
          <NavLink to="/tarefas">Tarefas</NavLink>
          <NavLink to="/medicamentos">Medicamentos</NavLink>
          <NavLink to="/rotina">Rotina</NavLink>
          <NavLink to="/alertas">Alertas</NavLink>
          <NavLink to="/painel-analitico">Painel analítico</NavLink>
          <NavLink to="/rede-de-confianca">Rede de confiança</NavLink>
          <NavLink to="/observando">Pessoas que acompanho</NavLink>
          <NavLink to="/plano-pessoal">Plano pessoal</NavLink>
          <NavLink to="/auditoria">Auditoria</NavLink>
        </nav>
        <div className="app-user">
          <span className="app-user__email">{user?.email}</span>
          <NavLink to="/configuracoes" className="button button--ghost">
            Configurações
          </NavLink>
          <button type="button" className="button button--ghost" onClick={() => void logout()}>
            Sair
          </button>
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
