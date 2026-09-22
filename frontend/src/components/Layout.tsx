import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import { CelebrationToast } from "./CelebrationToast";
import { OfflineBanner } from "./OfflineBanner";

/**
 * Redesign da Home (2026-09): navegação reduzida a 4 áreas (Agora /
 * Missões / Padrões / Mais) — nenhuma rota foi removida, só
 * reorganizada. "Painel analítico" (renomeado "Padrões" aqui, rota
 * inalterada) sai de dentro de "Mais" pra virar área própria; tudo
 * que não é ação do dia a dia (check-in avulso, medicamentos, alertas,
 * rotina, rede de confiança, observando, plano pessoal, notificações,
 * auditoria) continua acessível em "Mais", só que mais cheio agora.
 */
export function Layout() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const pathname = useLocation().pathname;
  const moreActive = [
    "/checkin",
    "/medicamentos",
    "/alertas",
    "/rotina",
    "/rede-de-confianca",
    "/observando",
    "/plano-pessoal",
    "/notificacoes",
    "/auditoria",
  ].some((path) => pathname.startsWith(path));

  return (
    <div className="app-shell">
      <OfflineBanner />
      <header className="app-header">
        <span className="app-name">Gancho</span>
        <nav className="app-nav" aria-label="Navegação principal">
          <NavLink to="/" end>
            Agora
          </NavLink>
          <NavLink to="/tarefas">Missões</NavLink>
          <NavLink to="/painel-analitico">Padrões</NavLink>
          <details className="app-more">
            <summary className={moreActive ? "active" : undefined}>Mais</summary>
            <div className="app-more__menu">
              <NavLink to="/checkin">Check-in</NavLink>
              <NavLink to="/medicamentos">Medicamentos</NavLink>
              <NavLink to="/alertas">Alertas</NavLink>
              <NavLink to="/rotina">Rotina</NavLink>
              <NavLink to="/rede-de-confianca">Rede de confiança</NavLink>
              <NavLink to="/observando">Pessoas que acompanho</NavLink>
              <NavLink to="/plano-pessoal">Plano pessoal</NavLink>
              <NavLink to="/notificacoes">Notificações</NavLink>
              <NavLink to="/auditoria">Auditoria</NavLink>
            </div>
          </details>
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
      <CelebrationToast />
    </div>
  );
}
