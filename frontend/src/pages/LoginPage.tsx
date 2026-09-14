import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { describeError } from "../api/client";
import { useAuthStore } from "../store/authStore";

export function LoginPage() {
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/", { replace: true });
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
          Ainda não tem conta? <Link to="/criar-conta">Criar conta</Link>
        </p>
      </form>
    </div>
  );
}
