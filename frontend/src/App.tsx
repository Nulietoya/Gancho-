import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AcceptInvitePage } from "./pages/AcceptInvitePage";
import { AccountSettingsPage } from "./pages/AccountSettingsPage";
import { AlertsPage } from "./pages/AlertsPage";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { AuditLogPage } from "./pages/AuditLogPage";
import { CheckinPage } from "./pages/CheckinPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ForgotPasswordPage } from "./pages/ForgotPasswordPage";
import { LoginPage } from "./pages/LoginPage";
import { MedicationsPage } from "./pages/MedicationsPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { PersonalPlanPage } from "./pages/PersonalPlanPage";
import { RegisterPage } from "./pages/RegisterPage";
import { ResetPasswordPage } from "./pages/ResetPasswordPage";
import { RoutinePage } from "./pages/RoutinePage";
import { TasksPage } from "./pages/TasksPage";
import { TrustedDashboardPage } from "./pages/TrustedDashboardPage";
import { TrustedPeoplePage } from "./pages/TrustedPeoplePage";
import { WatchingListPage } from "./pages/WatchingListPage";

export function App() {
  return (
    <Routes>
      <Route path="/entrar" element={<LoginPage />} />
      <Route path="/criar-conta" element={<RegisterPage />} />
      <Route path="/esqueci-senha" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/checkin" element={<CheckinPage />} />
          <Route path="/rede-de-confianca" element={<TrustedPeoplePage />} />
          <Route path="/aceitar-convite" element={<AcceptInvitePage />} />
          <Route path="/medicamentos" element={<MedicationsPage />} />
          <Route path="/notificacoes" element={<NotificationsPage />} />
          <Route path="/rotina" element={<RoutinePage />} />
          <Route path="/alertas" element={<AlertsPage />} />
          <Route path="/painel-analitico" element={<AnalyticsPage />} />
          <Route path="/plano-pessoal" element={<PersonalPlanPage />} />
          <Route path="/configuracoes" element={<AccountSettingsPage />} />
          <Route path="/observando" element={<WatchingListPage />} />
          <Route path="/observando/:relationshipId" element={<TrustedDashboardPage />} />
          <Route path="/auditoria" element={<AuditLogPage />} />
          <Route path="/tarefas" element={<TasksPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

