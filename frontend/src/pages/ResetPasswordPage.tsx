import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { describeError, rawJson } from "../api/client";

/**
 * Confirmação do reset de senha — a página que faltava por completo
 * no frontend. O backend sempre teve `POST /auth/password-reset/confirm`
 * e o e-mail sempre apontava pra `/reset-password?token=...`, mas essa
 * rota não existia: o link caía no catch-all do App.tsx e nunca dava
 * pra trocar a senha de verdade. Achado ao testar o envio de e-mail
 * real pela primeira vez (Resend), não durante a ETAPA 27 original.
 */
export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (newPassword !== confirmPassword) {
      setError("as senhas não coincidem");
      return;
    }

    setSubmitting(true);
    try {
      await rawJson("/auth/password-reset/confirm", {
        method: "POST",
        body: JSON.stringify({ token, new_password: newPassword }),
      });
      setDone(true);
    } catch (err) {
      setError(describeError(err, "não foi possível redefinir a senha"));
    } finally {
      setSubmitting(false);
    }
  }

  if (!token) {
    return (
      <div className="auth-page">
        <div className="auth-form">
          <h1>Gancho</h1>
          <p className="auth-subtitle">Link inválido</p>
          <p>Esse link de redefinição de senha está incompleto. Peça um novo link.</p>
          <p className="auth-switch">
            <Link to="/esqueci-senha">Pedir novo link</Link>
          </p>
        </div>
      </div>
    );
  }

  if (done) {
    return (
      <div className="auth-page">
        <div className="auth-form">
          <h1>Gancho</h1>
          <p className="auth-subtitle">Senha redefinida</p>
          <p>Sua senha foi trocada. Já pode entrar com a senha nova.</p>
          <Link to="/entrar" className="button">
            Ir para o login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <form className="auth-form" onSubmit={handleSubmit}>
        <h1>Gancho</h1>
        <p className="auth-subtitle">Definir nova senha</p>
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
        <label>
          Confirmar nova senha
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
          />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Salvando…" : "Redefinir senha"}
        </button>
        <p className="auth-switch">
          Link expirado ou inválido? <Link to="/esqueci-senha">Peça um novo</Link>
        </p>
      </form>
    </div>
  );
}
