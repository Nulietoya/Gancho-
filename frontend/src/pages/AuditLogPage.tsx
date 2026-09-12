import { useEffect, useState } from "react";
import { listAuditLog } from "../api/audit";
import { describeError } from "../api/client";
import type { AuditLogEntry } from "../api/types";
import { AUDIT_ACTION_LABELS } from "../labels";

const PAGE_SIZE = 50;

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR");
}

function MetadataLine({ metadata }: { metadata: Record<string, unknown> | null }) {
  if (!metadata || Object.keys(metadata).length === 0) return null;
  const parts = Object.entries(metadata).map(([key, value]) => `${key}: ${String(value)}`);
  return <p className="relationship-card__email">{parts.join(" — ")}</p>;
}

export function AuditLogPage() {
  const [offset, setOffset] = useState(0);
  const [entries, setEntries] = useState<AuditLogEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setEntries(null);
    listAuditLog(PAGE_SIZE, offset)
      .then((result) => {
        if (!cancelled) setEntries(result);
      })
      .catch((err) => {
        if (!cancelled) setError(describeError(err, "não foi possível carregar a auditoria"));
      });
    return () => {
      cancelled = true;
    };
  }, [offset]);

  const hasNextPage = (entries?.length ?? 0) === PAGE_SIZE;

  return (
    <div className="trusted-people-page">
      <h1>Auditoria</h1>
      <p className="checkin-hint">
        O que aconteceu com a sua própria conta — nunca revela qual pessoa de confiança específica agiu, só que "não
        foi você mesmo(a)".
      </p>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {entries === null && !error && <p className="checkin-hint">carregando…</p>}
      {entries !== null && entries.length === 0 && (
        <p className="checkin-hint">
          {offset === 0 ? "nenhum registro ainda." : "nenhum registro nesta página."}
        </p>
      )}
      {entries !== null && entries.length > 0 && (
        <ul className="plain-list">
          {entries.map((entry) => (
            <li key={entry.id}>
              <strong>{AUDIT_ACTION_LABELS[entry.action]}</strong>
              {!entry.actor_is_self && <span className="status-badge status-badge--pending">não foi você</span>}
              <p className="relationship-card__dates">{formatDateTime(entry.created_at)}</p>
              <MetadataLine metadata={entry.metadata} />
            </li>
          ))}
        </ul>
      )}

      <div className="relationship-card__actions">
        <button
          type="button"
          className="button button--ghost"
          onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
          disabled={offset === 0}
        >
          Anterior
        </button>
        <button
          type="button"
          className="button button--ghost"
          onClick={() => setOffset((o) => o + PAGE_SIZE)}
          disabled={!hasNextPage}
        >
          Próxima
        </button>
      </div>
    </div>
  );
}
