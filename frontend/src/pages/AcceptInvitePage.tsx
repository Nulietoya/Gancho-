import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { acceptInvite } from "../api/trustedPeople";
import { describeError } from "../api/client";
import type { RelationshipPublic } from "../api/types";

export function AcceptInvitePage() {
  const [searchParams] = useSearchParams();
  // O e-mail de convite (e o link manual mostrado pra quem convidou)
  // já trazem `?token=...` — preenche sozinho, mas continua editável
  // pra quem preferir colar o código na mão.
  const [token, setToken] = useState(searchParams.get("token") ?? "");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [accepted, setAccepted] = useState<RelationshipPublic | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
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
            Você agora é pessoa de confiança de <strong>{accepted.invite_email}</strong>. O que você vai poder ver
            ou fazer depende das permissões que essa pessoa conceder a você — nada aparece por padrão.
          </p>
          <Link to="/observando" className="button">
            Ver painel
          </Link>
        </section>
      </div>
    );
  }

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
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button type="submit" className="button" disabled={submitting}>
            {submitting ? "Aceitando…" : "Aceitar convite"}
          </button>
        </form>
      </section>
    </div>
  );
}
