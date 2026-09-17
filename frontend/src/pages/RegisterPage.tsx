import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { describeError } from "../api/client";
import { useAuthStore } from "../store/authStore";

/** Mesma trava de `LoginPage` — nunca segue um `redirect` pra fora do app. */
function safeRedirect(raw: string | null): string {
  if (raw && raw.startsWith("/") && !raw.startsWith("//")) return raw;
  return "/";
}

export function RegisterPage() {
  const register = useAuthStore((s) => s.register);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  // Mesmo propósito de `LoginPage`: volta pro link de convite depois
  // de criar a conta, em vez de cair no painel "/" sem contexto.
  const redirect = safeRedirect(searchParams.get("redirect"));
  const [email, setEmail] = useState(searchParams.get("email") ?? "");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("as senhas não coincidem");
      return;
    }

    setSubmitting(true);
    try {
      await register(email, password);
      navigate(redirect, { replace: true });
    } catch (err) {
      setError(describeError(err, "não foi possível criar a conta"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-form" onSubmit={handleSubmit}>
        <h1>Gancho</h1>
        <p className="auth-subtitle">Criar sua conta</p>
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
            minLength={8}
            autoComplete="new-password"
          />
        </label>
        <p className="field-hint">Pelo menos 8 caracteres, com letra e número.</p>
        <label>
          Confirmar senha
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            autoComplete="new-password"
          />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Criando conta…" : "Criar conta"}
        </button>
        <p className="auth-switch">
          Já tem conta?{" "}
          <Link to={`/entrar?${new URLSearchParams({ redirect, ...(email ? { email } : {}) }).toString()}`}>
            Entrar
          </Link>
        </p>
      </form>
    </div>
  );
}
