import { useEffect, useState, type FormEvent } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { acceptInvite, previewInvite } from "../api/trustedPeople";
import { describeError } from "../api/client";
import { useAuthStore } from "../store/authStore";
import type { InvitePreview, RelationshipAsTrustedPublic } from "../api/types";

type PreviewState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "loaded"; data: InvitePreview }
  | { status: "not_found" };

/**
 * Bug real corrigido aqui (achado investigando um convite de verdade
 * que não funcionou em produção — ver docs/decisions.md): esta
 * página ficava dentro do `ProtectedRoute`, então quem abrisse o
 * link do convite SEM já estar logado era jogado pra `/entrar` e
 * perdia o `?token=` — sem forma de voltar pra aqui depois de criar
 * conta ou entrar. Agora a página é pública (`App.tsx`) e decide
 * sozinha o que mostrar: sem sessão, guia pra login/cadastro
 * preservando o link exato de volta; logado com e-mail diferente do
 * convite, avisa isso ANTES de deixar tentar (a causa real, mais
 * comum, de "convite inválido" sem explicação nenhuma).
 */
export function AcceptInvitePage() {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const status = useAuthStore((s) => s.status);
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const [token, setToken] = useState(searchParams.get("token") ?? "");
  const [preview, setPreview] = useState<PreviewState>({ status: "idle" });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [accepted, setAccepted] = useState<RelationshipAsTrustedPublic | null>(null);

  useEffect(() => {
    const trimmed = token.trim();
    if (!trimmed) {
      setPreview({ status: "idle" });
      return;
    }
    let cancelled = false;
    setPreview({ status: "loading" });
    previewInvite(trimmed)
      .then((data) => {
        if (!cancelled) setPreview({ status: "loaded", data });
      })
      .catch(() => {
        if (!cancelled) setPreview({ status: "not_found" });
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  const currentPath = `${location.pathname}${location.search}`;
  const invitedEmail = preview.status === "loaded" ? preview.data.invite_email : null;
  const authRedirectParams = new URLSearchParams({ redirect: currentPath });
  if (invitedEmail) authRedirectParams.set("email", invitedEmail);
  const loginHref = `/entrar?${authRedirectParams.toString()}`;
  const registerHref = `/criar-conta?${authRedirectParams.toString()}`;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (status !== "authenticated") return; // sem sessão, não tem token de acesso pra chamar a API
    setError(null);
    setSubmitting(true);
    try {
      const relationship = await acceptInvite(token.trim());
      setAccepted(relationship);
    } catch (err) {
      setError(describeError(err, "não foi possível aceitar o convite"));
    } finally {
      setSubmitting(false);
    }
  }

  if (accepted) {
    return (
      <div className="trusted-people-page">
        <h1>Convite aceito</h1>
        <section className="card">
          <p>
            Você agora é pessoa de confiança de <strong>{accepted.owner_display_name}</strong>. O que você vai
            poder ver ou fazer depende das permissões que essa pessoa conceder a você — nada aparece por padrão.
          </p>
          <Link to="/observando" className="button">
            Ver painel
          </Link>
        </section>
      </div>
    );
  }

  if (status === "idle" || status === "loading") {
    return <p className="page-loading">carregando…</p>;
  }

  const emailMismatch =
    status === "authenticated" &&
    user &&
    preview.status === "loaded" &&
    user.email.toLowerCase() !== preview.data.invite_email.toLowerCase();

  return (
    <div className="trusted-people-page">
      <h1>Aceitar um convite</h1>
      <section className="card">
        <p className="checkin-hint">
          Cole aqui o código de convite que você recebeu para se tornar pessoa de confiança de alguém.
        </p>
        <form className="invite-form" onSubmit={handleSubmit}>
          <label>
            Código do convite
            <input type="text" value={token} onChange={(e) => setToken(e.target.value)} required />
          </label>

          {preview.status === "not_found" && token.trim() && (
            <p className="form-error" role="alert">
              este código de convite não foi encontrado — confira se copiou o link completo.
            </p>
          )}

          {preview.status === "loaded" && preview.data.status === "revoked" && (
            <p className="form-error" role="alert">
              este convite foi revogado por quem convidou — peça um novo.
            </p>
          )}

          {preview.status === "loaded" && preview.data.status === "pending" && (
            <p className="checkin-hint">
              Convite de <strong>{preview.data.owner_display_name}</strong> para{" "}
              <strong>{preview.data.invite_email}</strong>.
            </p>
          )}

          {preview.status === "loaded" && preview.data.status === "accepted" && (
            <p className="checkin-hint">este convite já foi aceito.</p>
          )}

          {status === "authenticated" && !emailMismatch && (
            <>
              {error && (
                <p className="form-error" role="alert">
                  {error}
                </p>
              )}
              <button type="submit" className="button" disabled={submitting}>
                {submitting ? "Aceitando…" : "Aceitar convite"}
              </button>
            </>
          )}
        </form>

        {status === "unauthenticated" && (
          <div className="card" style={{ marginTop: "1rem" }}>
            <p>
              {invitedEmail
                ? `Para aceitar, entre ou crie uma conta com o e-mail ${invitedEmail} — o e-mail exato para o qual este convite foi enviado.`
                : "Para aceitar um convite, você precisa entrar ou criar uma conta primeiro. Cole o código acima pra ver de quem é o convite."}
            </p>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <Link to={loginHref} className="button">
                Entrar
              </Link>
              <Link to={registerHref} className="button button--ghost">
                Criar conta
              </Link>
            </div>
          </div>
        )}

        {status === "authenticated" && emailMismatch && (
          <div className="card" style={{ marginTop: "1rem" }}>
            <p className="form-error" role="alert">
              Você está logado como <strong>{user?.email}</strong>, mas este convite foi enviado para{" "}
              <strong>{preview.status === "loaded" && preview.data.invite_email}</strong>. Saia e entre (ou crie
              uma conta) com esse e-mail antes de aceitar — o convite não funciona com uma conta diferente.
            </p>
            <button type="button" className="button button--ghost" onClick={() => void logout()}>
              Sair
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
