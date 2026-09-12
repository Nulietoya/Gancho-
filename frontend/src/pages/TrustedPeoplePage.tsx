import { useEffect, useState, type FormEvent } from "react";
import { describeError } from "../api/client";
import {
  inviteTrustedPerson,
  listObservations,
  listTrustedPeople,
  revokeRelationship,
  updatePermissions,
} from "../api/trustedPeople";
import type { ObservationPublic, PermissionUpdate, RelationshipPublic } from "../api/types";
import { PermissionEditor } from "../components/PermissionEditor";
import {
  OBSERVATION_CATEGORY_LABELS,
  OBSERVATION_INTENSITY_LABELS,
  OBSERVATION_SINCE_LABELS,
  RELATIONSHIP_STATUS_LABELS,
} from "../labels";

function formatDate(iso: string | null): string | null {
  if (!iso) return null;
  return new Date(iso).toLocaleDateString("pt-BR");
}

function InviteForm({ onInvited }: { onInvited: (relationship: RelationshipPublic) => void }) {
  const [email, setEmail] = useState("");
  const [label, setLabel] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const relationship = await inviteTrustedPerson(email, label.trim() || null);
      onInvited(relationship);
      setEmail("");
      setLabel("");
    } catch (err) {
      setError(describeError(err, "não foi possível enviar o convite"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="card">
      <h2>Convidar pessoa de confiança</h2>
      <p className="checkin-hint">
        Ela recebe acesso só ao que você autorizar depois, permissão por permissão — nunca vê tudo automaticamente
        por aceitar o convite.
      </p>
      <form className="invite-form" onSubmit={handleSubmit}>
        <label>
          E-mail da pessoa
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Como você a chama (opcional)
          <input
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="ex.: minha irmã, meu terapeuta"
            maxLength={80}
          />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Enviando…" : "Enviar convite"}
        </button>
      </form>
    </section>
  );
}

function ObservationsList({ relationshipId }: { relationshipId: string }) {
  const [observations, setObservations] = useState<ObservationPublic[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listObservations(relationshipId)
      .then((result) => {
        if (!cancelled) setObservations(result);
      })
      .catch((err) => {
        if (!cancelled) setError(describeError(err, "não foi possível carregar as observações"));
      });
    return () => {
      cancelled = true;
    };
  }, [relationshipId]);

  if (error) {
    return (
      <p className="form-error" role="alert">
        {error}
      </p>
    );
  }
  if (observations === null) {
    return <p className="checkin-hint">carregando…</p>;
  }
  if (observations.length === 0) {
    return <p className="checkin-hint">nenhuma observação registrada por essa pessoa ainda.</p>;
  }
  return (
    <ul className="plain-list">
      {observations.map((obs) => (
        <li key={obs.id} className="observation-item">
          <strong>{OBSERVATION_CATEGORY_LABELS[obs.category]}</strong> — {OBSERVATION_SINCE_LABELS[obs.since]}, intensidade{" "}
          {OBSERVATION_INTENSITY_LABELS[obs.intensity]}
          {obs.note && <p className="observation-note">"{obs.note}"</p>}
          <span className="observation-date">{formatDate(obs.recorded_at)}</span>
        </li>
      ))}
    </ul>
  );
}

function RelationshipCard({
  relationship,
  onUpdated,
}: {
  relationship: RelationshipPublic;
  onUpdated: (relationship: RelationshipPublic) => void;
}) {
  const [showPermissions, setShowPermissions] = useState(false);
  const [showObservations, setShowObservations] = useState(false);
  const [confirmingRevoke, setConfirmingRevoke] = useState(false);
  const [revoking, setRevoking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSavePermissions(updates: PermissionUpdate[]) {
    const updated = await updatePermissions(relationship.id, updates);
    onUpdated(updated);
  }

  async function handleRevoke() {
    setRevoking(true);
    setError(null);
    try {
      const updated = await revokeRelationship(relationship.id);
      onUpdated(updated);
    } catch (err) {
      setError(describeError(err, "não foi possível revogar"));
    } finally {
      setRevoking(false);
      setConfirmingRevoke(false);
    }
  }

  const isAccepted = relationship.status === "accepted";
  const isRevoked = relationship.status === "revoked";

  return (
    <li className="card relationship-card">
      <div className="relationship-card__header">
        <div>
          <strong>{relationship.relationship_label || relationship.invite_email}</strong>
          {relationship.relationship_label && (
            <p className="relationship-card__email">{relationship.invite_email}</p>
          )}
        </div>
        <span className={`status-badge status-badge--${relationship.status}`}>
          {RELATIONSHIP_STATUS_LABELS[relationship.status]}
        </span>
      </div>

      <p className="relationship-card__dates">
        {relationship.status === "pending" && `convite enviado em ${formatDate(relationship.invited_at)}`}
        {isAccepted && `pessoa de confiança desde ${formatDate(relationship.accepted_at)}`}
        {isRevoked && `revogado em ${formatDate(relationship.revoked_at)}`}
      </p>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      {isAccepted && (
        <div className="relationship-card__actions">
          <button type="button" className="button button--ghost" onClick={() => setShowPermissions((v) => !v)}>
            {showPermissions ? "Ocultar permissões" : "Gerenciar permissões"}
          </button>
          <button type="button" className="button button--ghost" onClick={() => setShowObservations((v) => !v)}>
            {showObservations ? "Ocultar observações" : "Ver observações registradas"}
          </button>
        </div>
      )}

      {showPermissions && isAccepted && (
        <PermissionEditor permissions={relationship.permissions} onSave={handleSavePermissions} />
      )}

      {showObservations && isAccepted && <ObservationsList relationshipId={relationship.id} />}

      {!isRevoked && (
        <div className="relationship-card__revoke">
          {confirmingRevoke ? (
            <>
              <span>Revogar o acesso dessa pessoa por completo?</span>
              <button type="button" className="button button--danger" onClick={() => void handleRevoke()} disabled={revoking}>
                {revoking ? "Revogando…" : "Sim, revogar"}
              </button>
              <button type="button" className="button button--ghost" onClick={() => setConfirmingRevoke(false)}>
                Cancelar
              </button>
            </>
          ) : (
            <button type="button" className="button button--ghost" onClick={() => setConfirmingRevoke(true)}>
              Revogar acesso
            </button>
          )}
        </div>
      )}
    </li>
  );
}

export function TrustedPeoplePage() {
  const [relationships, setRelationships] = useState<RelationshipPublic[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listTrustedPeople()
      .then((result) => {
        if (!cancelled) setRelationships(result);
      })
      .catch((err) => {
        if (!cancelled) setError(describeError(err, "não foi possível carregar sua rede de confiança"));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function handleInvited(relationship: RelationshipPublic) {
    setRelationships((prev) => [relationship, ...(prev ?? [])]);
  }

  function handleUpdated(updated: RelationshipPublic) {
    setRelationships((prev) => (prev ?? []).map((r) => (r.id === updated.id ? updated : r)));
  }

  return (
    <div className="trusted-people-page">
      <h1>Rede de confiança</h1>
      <p className="checkin-hint">
        Pessoas que podem receber alertas ou apoiar você, sempre segundo as permissões que você conceder — e que
        pode revogar a qualquer momento.
      </p>

      <InviteForm onInvited={handleInvited} />

      <section>
        <h2>Suas pessoas de confiança</h2>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {relationships === null && !error && <p className="checkin-hint">carregando…</p>}
        {relationships !== null && relationships.length === 0 && (
          <p className="checkin-hint">você ainda não convidou ninguém.</p>
        )}
        {relationships !== null && relationships.length > 0 && (
          <ul className="relationship-list">
            {relationships.map((relationship) => (
              <RelationshipCard key={relationship.id} relationship={relationship} onUpdated={handleUpdated} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
