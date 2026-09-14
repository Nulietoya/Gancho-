import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { describeError, rawJson } from "../api/client";

/**
 * Pedido de reset de senha (item 35 / ETAPA 22 — o passo que faltava
 * de verdade: o backend sempre teve `POST /auth/password-reset/request`,
 * mas nenhuma tela do frontend chamava esse endpoint; a única forma de
 * disparar um reset era chamar a API na mão).
 *
 * Sempre mostra a mesma mensagem de sucesso, exista ou não a conta com
 * esse e-mail — o próprio backend já responde 202 nos dois casos por
 * essa razão (evita que alguém descubra quais e-mails têm conta); a
 * tela só respeita esse contrato.
 */
export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await rawJson("/auth/password-reset/request", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setSent(true);
    } catch (err) {
      setError(describeError(err, "não foi possível enviar o e-mail de recuperação"));
    } finally {
      setSubmitting(false);
    }
  }

  if (sent) {
    return (
      <div className="auth-page">
        <div className="auth-form">
          <h1>Gancho</h1>
          <p className="auth-subtitle">Verifique seu e-mail</p>
          <p>
            Se <strong>{email}</strong> tiver uma conta, um e-mail com instruções pra redefinir a senha foi enviado
            (o link expira em 30 minutos). Não chegou? Confira a caixa de spam antes de tentar de novo.
          </p>
          <p className="auth-switch">
            <Link to="/entrar">Voltar pra entrar</Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <form className="auth-form" onSubmit={handleSubmit}>
        <h1>Gancho</h1>
        <p className="auth-subtitle">Esqueci minha senha</p>
        <label>
          E-mail da conta
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Enviando…" : "Enviar link de recuperação"}
        </button>
        <p className="auth-switch">
          <Link to="/entrar">Voltar pra entrar</Link>
        </p>
      </form>
    </div>
  );
}
