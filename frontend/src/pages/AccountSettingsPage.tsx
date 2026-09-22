import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { changePassword, deleteAccount, exportAndDownloadAccountData } from "../api/account";
import { describeError } from "../api/client";
import { useAuthStore } from "../store/authStore";
import { useThemeStore } from "../store/themeStore";

function AppearanceSection() {
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);

  return (
    <section className="card">
      <h2>Aparência</h2>
      <p className="checkin-hint">
        O padrão agora é o visual escuro, mais direto. O claro "Companheiro calmo" (o padrão original do app)
        continua disponível pra quem prefere — muda só a cor, nada na forma como o app funciona.
      </p>
      <div className="theme-switch" role="radiogroup" aria-label="Tema">
        <button
          type="button"
          role="radio"
          aria-checked={theme === "dark"}
          className={`button ${theme === "dark" ? "" : "button--ghost"}`}
          onClick={() => setTheme("dark")}
        >
          Escuro (padrão)
        </button>
        <button
          type="button"
          role="radio"
          aria-checked={theme === "light"}
          className={`button ${theme === "light" ? "" : "button--ghost"}`}
          onClick={() => setTheme("light")}
        >
          Claro
        </button>
      </div>
    </section>
  );
}

function ChangePasswordSection() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccess(false);
    setSubmitting(true);
    try {
      await changePassword({ current_password: currentPassword, new_password: newPassword });
      setSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
    } catch (err) {
      setError(describeError(err, "não foi possível trocar a senha"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="card">
      <h2>Trocar senha</h2>
      <form className="invite-form" onSubmit={handleSubmit}>
        <label>
          Senha atual
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </label>
        <label>
          Nova senha
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
          />
        </label>
        <p className="checkin-hint">Pelo menos 8 caracteres, com letra e número.</p>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {success && <p className="checkin-hint">Senha atualizada.</p>}
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Salvando…" : "Trocar senha"}
        </button>
      </form>
    </section>
  );
}

function ExportDataSection() {
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [done, setDone] = useState(false);

  async function handleExport() {
    setError(null);
    setExporting(true);
    setDone(false);
    try {
      await exportAndDownloadAccountData();
      setDone(true);
    } catch (err) {
      setError(describeError(err, "não foi possível exportar seus dados"));
    } finally {
      setExporting(false);
    }
  }

  return (
    <section className="card">
      <h2>Exportar meus dados</h2>
      <p className="checkin-hint">
        Baixa um arquivo JSON com tudo que sua conta gerou ou recebeu — perfil, check-ins, rotina, medicamentos,
        intervenções, plano pessoal e sua rede de confiança. Nunca inclui sua senha nem dados de outra pessoa além
        do relacionamento.
      </p>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {done && <p className="checkin-hint">Download iniciado.</p>}
      <button type="button" className="button button--ghost" onClick={() => void handleExport()} disabled={exporting}>
        {exporting ? "Preparando…" : "Baixar meus dados (JSON)"}
      </button>
    </section>
  );
}

const DELETE_CONFIRMATION_WORD = "EXCLUIR";

function DeleteAccountSection() {
  const navigate = useNavigate();
  const logout = useAuthStore((s) => s.logout);
  const [confirming, setConfirming] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmationText, setConfirmationText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleConfirm(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await deleteAccount({ password });
      // a conta já não existe mais no banco — o logout local só limpa
      // o estado local (a chamada a /auth/logout dentro dele é
      // best-effort e tolera o refresh token já não existir mais).
      await logout();
      navigate("/entrar", { replace: true });
    } catch (err) {
      setError(describeError(err, "não foi possível excluir a conta"));
      setSubmitting(false);
    }
  }

  return (
    <section className="card">
      <h2>Excluir conta</h2>
      <p className="checkin-hint">
        Apaga sua conta e todo o dado ligado a ela — tarefas, check-ins, medicações, rotina, plano pessoal,
        notificações — de forma definitiva e imediata. Não é desativação: não tem como desfazer depois.
        Relacionamentos de confiança em que você é a pessoa dona somem junto; se você é pessoa de confiança de
        alguém, esse acesso é revogado, mas a conta da outra pessoa continua intacta.
      </p>
      {!confirming && (
        <button type="button" className="button button--danger" onClick={() => setConfirming(true)}>
          Excluir minha conta
        </button>
      )}
      {confirming && (
        <form className="invite-form" onSubmit={handleConfirm}>
          <label>
            Confirme sua senha
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </label>
          <label>
            Digite <strong>{DELETE_CONFIRMATION_WORD}</strong> para confirmar
            <input
              type="text"
              value={confirmationText}
              onChange={(e) => setConfirmationText(e.target.value)}
              required
              autoComplete="off"
            />
          </label>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <div className="relationship-card__revoke">
            <button
              type="submit"
              className="button button--danger"
              disabled={submitting || confirmationText !== DELETE_CONFIRMATION_WORD}
            >
              {submitting ? "Excluindo…" : "Sim, excluir minha conta para sempre"}
            </button>
            <button
              type="button"
              className="button button--ghost"
              onClick={() => {
                setConfirming(false);
                setPassword("");
                setConfirmationText("");
                setError(null);
              }}
            >
              Cancelar
            </button>
          </div>
        </form>
      )}
    </section>
  );
}

export function AccountSettingsPage() {
  return (
    <div className="trusted-people-page">
      <h1>Configurações de conta</h1>
      <AppearanceSection />
      <ChangePasswordSection />
      <ExportDataSection />
      <DeleteAccountSection />
    </div>
  );
}
