import { useEffect, useState } from "react";
import {
  acknowledgeAlert,
  explainAlert,
  getCurrentAlert,
  listAlertHistory,
  resolveAlert,
  syncAlertState,
} from "../api/alerts";
import { describeError } from "../api/client";
import { runAllEngines } from "../api/deviation";
import type { AlertExplanation, AlertPublic } from "../api/types";
import { StateBadge } from "../components/StateBadge";

function formatDateTime(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString("pt-BR");
}

function ExplanationView({ explanation }: { explanation: AlertExplanation }) {
  return (
    <div className="explanation">
      <p className="checkin-hint">
        {explanation.engines_count} de {explanation.total_engines} motores convergindo agora
        {explanation.breadth_score !== null && ` (${Math.round(explanation.breadth_score * 100)}% das áreas)`}.
      </p>
      {explanation.engines.length === 0 && (
        <p className="checkin-hint">nenhum motor com desvio ativo no momento.</p>
      )}
      {explanation.engines.map((engine) => (
        <div key={engine.engine} className="engine-card">
          <h3>{engine.engine_label}</h3>
          <p>{engine.explanation}</p>
          <p className="checkin-hint">
            há {engine.duration_days} dia(s)
            {engine.convergence_score !== null && ` — convergência ${engine.convergence_score.toFixed(2)}`}
          </p>
          <ul className="plain-list">
            {engine.indicators.map((ind) => (
              <li key={ind.indicator_key}>
                <strong>{ind.label}</strong>
                {ind.baseline_mean !== null && ind.recent_value !== null && (
                  <span>
                    {" "}
                    — seu normal {ind.baseline_mean.toFixed(1)}, agora {ind.recent_value.toFixed(1)}
                    {ind.direction && ` (${ind.direction})`}
                  </span>
                )}
                {ind.streak_days !== null && <span> — {ind.streak_days} dia(s) seguidos</span>}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function CurrentAlertCard({
  alert,
  onChanged,
}: {
  alert: AlertPublic;
  onChanged: (alert: AlertPublic) => void;
}) {
  const [explanation, setExplanation] = useState<AlertExplanation | null>(null);
  const [showExplanation, setShowExplanation] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingExplanation, setLoadingExplanation] = useState(false);
  const [acting, setActing] = useState(false);

  async function toggleExplanation() {
    if (showExplanation) {
      setShowExplanation(false);
      return;
    }
    setShowExplanation(true);
    if (!explanation) {
      setLoadingExplanation(true);
      try {
        setExplanation(await explainAlert(alert.id));
      } catch (err) {
        setError(describeError(err, "não foi possível carregar a explicação"));
      } finally {
        setLoadingExplanation(false);
      }
    }
  }

  async function handleAcknowledge() {
    setActing(true);
    try {
      onChanged(await acknowledgeAlert(alert.id));
    } catch (err) {
      setError(describeError(err, "não foi possível confirmar"));
    } finally {
      setActing(false);
    }
  }

  async function handleResolve() {
    setActing(true);
    try {
      onChanged(await resolveAlert(alert.id));
    } catch (err) {
      setError(describeError(err, "não foi possível marcar como resolvido"));
    } finally {
      setActing(false);
    }
  }

  return (
    <section className="card">
      <h2>Seu estado agora</h2>
      <StateBadge state={alert.state} reason={alert.reason_summary} />
      <p className="checkin-hint">desde {formatDateTime(alert.created_at)}</p>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      <div className="relationship-card__actions">
        <button type="button" className="button button--ghost" onClick={() => void toggleExplanation()}>
          {showExplanation ? "Ocultar explicação" : "Ver por que estou nesse estado"}
        </button>
        {!alert.acknowledged_at && (
          <button type="button" className="button button--ghost" onClick={() => void handleAcknowledge()} disabled={acting}>
            Já vi
          </button>
        )}
        {!alert.resolved_at && alert.state !== "green" && (
          <button type="button" className="button button--ghost" onClick={() => void handleResolve()} disabled={acting}>
            Marcar como resolvido
          </button>
        )}
      </div>

      {showExplanation && (
        <>
          {loadingExplanation && <p className="checkin-hint">carregando…</p>}
          {explanation && <ExplanationView explanation={explanation} />}
        </>
      )}
    </section>
  );
}

export function AlertsPage() {
  const [current, setCurrent] = useState<AlertPublic | null | undefined>(undefined);
  const [history, setHistory] = useState<AlertPublic[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recalculating, setRecalculating] = useState(false);

  async function loadAll() {
    try {
      const [currentAlert, historyList] = await Promise.all([getCurrentAlert(), listAlertHistory(30)]);
      setCurrent(currentAlert);
      setHistory(historyList);
    } catch (err) {
      setError(describeError(err, "não foi possível carregar seus alertas"));
    }
  }

  useEffect(() => {
    void loadAll();
  }, []);

  async function handleRecalculate() {
    setRecalculating(true);
    setError(null);
    try {
      await runAllEngines();
      await syncAlertState();
      await loadAll();
    } catch (err) {
      setError(describeError(err, "não foi possível recalcular"));
    } finally {
      setRecalculating(false);
    }
  }

  function handleCurrentChanged(updated: AlertPublic) {
    setCurrent(updated);
    setHistory((prev) => (prev ?? []).map((a) => (a.id === updated.id ? updated : a)));
  }

  return (
    <div className="trusted-people-page">
      <h1>Alertas e explicação</h1>
      <p className="checkin-hint">
        Seu estado nunca é um diagnóstico — é a comparação entre o seu funcionamento agora e o seu próprio padrão
        habitual, nunca uma média de outras pessoas.
      </p>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      <div className="relationship-card__actions">
        <button type="button" className="button button--ghost" onClick={() => void handleRecalculate()} disabled={recalculating}>
          {recalculating ? "Recalculando…" : "Recalcular agora"}
        </button>
      </div>

      {current === undefined && !error && <p className="checkin-hint">carregando…</p>}

      {current === null && (
        <section className="card">
          <p>Ainda não há um estado calculado. Isso roda sozinho toda noite, ou você pode calcular agora.</p>
        </section>
      )}

      {current && <CurrentAlertCard alert={current} onChanged={handleCurrentChanged} />}

      <section>
        <h2>Histórico</h2>
        {history === null && <p className="checkin-hint">carregando…</p>}
        {history !== null && history.length === 0 && <p className="checkin-hint">nenhum registro ainda.</p>}
        {history !== null && history.length > 0 && (
          <ul className="relationship-list">
            {history.map((a) => (
              <li key={a.id} className="card relationship-card">
                <div className="relationship-card__header">
                  <div>
                    <span className={`status-badge status-badge--${a.state === "green" ? "accepted" : a.state === "yellow" ? "pending" : "revoked"}`}>
                      {a.state === "green" ? "verde" : a.state === "yellow" ? "amarelo" : "vermelho"}
                    </span>
                  </div>
                </div>
                <p>{a.reason_summary}</p>
                <p className="relationship-card__dates">
                  {formatDateTime(a.created_at)}
                  {a.resolved_at && ` — resolvido em ${formatDateTime(a.resolved_at)}`}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
