import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { describeError } from "../api/client";
import { useAuthStore } from "../store/authStore";

/**
 * Só volta pra dentro do próprio app — nunca segue um `redirect` que
 * apontasse pra outro site (ex.: link de e-mail malicioso tentando
 * usar este parâmetro pra phishing). Precisa começar com "/" e nunca
 * com "//" (que o navegador trata como protocolo-relativo).
 */
function safeRedirect(raw: string | null): string {
  if (raw && raw.startsWith("/") && !raw.startsWith("//")) return raw;
  return "/";
}

export function LoginPage() {
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  // Preserva pra onde a pessoa estava indo — hoje só usado pelo link
  // de convite (`/aceitar-convite?token=...`), que precisa levar a
  // pessoa de volta pra lá depois de entrar, e não pro painel "/".
  const redirect = safeRedirect(searchParams.get("redirect"));
  const [email, setEmail] = useState(searchParams.get("email") ?? "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate(redirect, { replace: true });
    } catch (err) {
      setError(describeError(err, "não foi possível entrar"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-form" onSubmit={handleSubmit}>
        <h1>Gancho</h1>
        <p className="auth-subtitle">Entrar na sua conta</p>
        <label>
          E-mail
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </label>
        <label>
          Senha
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Entrando…" : "Entrar"}
        </button>
        <p className="auth-switch">
          <Link to="/esqueci-senha">Esqueci minha senha</Link>
        </p>
        <p className="auth-switch">
          Ainda não tem conta?{" "}
          <Link
            to={`/criar-conta?${new URLSearchParams({ redirect, ...(email ? { email } : {}) }).toString()}`}
          >
            Criar conta
          </Link>
        </p>
      </form>
    </div>
  );
}
