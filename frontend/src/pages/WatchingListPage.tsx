import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { describeError } from "../api/client";
import { listWatchedAccounts } from "../api/trustedPeople";
import type { RelationshipAsTrustedPublic } from "../api/types";

function formatDate(iso: string | null): string | null {
  if (!iso) return null;
  return new Date(iso).toLocaleDateString("pt-BR");
}

export function WatchingListPage() {
  const [relationships, setRelationships] = useState<RelationshipAsTrustedPublic[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listWatchedAccounts()
      .then((result) => {
        if (!cancelled) setRelationships(result);
      })
      .catch((err) => {
        if (!cancelled) setError(describeError(err, "não foi possível carregar sua lista"));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="trusted-people-page">
      <h1>Pessoas que você acompanha</h1>
      <p className="checkin-hint">
        O que você vê de cada conta depende só das permissões que aquela pessoa concedeu a você — nunca aparece mais
        do que ela autorizou.
      </p>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {relationships === null && !error && <p className="checkin-hint">carregando…</p>}
      {relationships !== null && relationships.length === 0 && (
        <p className="checkin-hint">
          você ainda não é pessoa de confiança aceita de ninguém. Peça pra essa pessoa te convidar em "Rede de
          confiança" dela.
        </p>
      )}
      {relationships !== null && relationships.length > 0 && (
        <ul className="relationship-list">
          {relationships.map((r) => (
            <li key={r.id} className="card relationship-card">
              <div className="relationship-card__header">
                <div>
                  <strong>{r.relationship_label || r.owner_display_name}</strong>
                  {r.relationship_label && <p className="relationship-card__email">{r.owner_display_name}</p>}
                </div>
              </div>
              <p className="relationship-card__dates">pessoa de confiança desde {formatDate(r.accepted_at)}</p>
              <div className="relationship-card__actions">
                <Link to={`/observando/${r.id}`} className="button button--ghost">
                  Ver painel
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
