import { useEffect, useState } from "react";
import { getAnalyticsDashboard } from "../api/analytics";
import { describeError } from "../api/client";
import { explainDeviationEvent } from "../api/deviation";
import type { AnalyticsDashboard, DeviationTimelineEntry, EngineExplanation } from "../api/types";

const PERIOD_OPTIONS = [7, 30, 90, 365];

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR");
}

function trendLabel(slope: number | null): string {
  if (slope === null) return "";
  if (slope > 0.01) return "subindo";
  if (slope < -0.01) return "descendo";
  return "estável";
}

function DeviationEventRow({ entry }: { entry: DeviationTimelineEntry }) {
  const [showDetails, setShowDetails] = useState(false);
  const [explanation, setExplanation] = useState<EngineExplanation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function toggle() {
    if (showDetails) {
      setShowDetails(false);
      return;
    }
    setShowDetails(true);
    if (!explanation) {
      setLoading(true);
      try {
        setExplanation(await explainDeviationEvent(entry.id));
      } catch (err) {
        setError(describeError(err, "não foi possível carregar os detalhes"));
      } finally {
        setLoading(false);
      }
    }
  }

  return (
    <li className="card relationship-card">
      <strong>{entry.engine_label}</strong>
      <p className="relationship-card__dates">
        detectado em {formatDate(entry.detected_at)} — {entry.duration_days} dia(s) de duração
      </p>
      <div className="relationship-card__actions">
        <button type="button" className="button button--ghost" onClick={() => void toggle()}>
          {showDetails ? "Ocultar detalhes" : "Ver detalhes"}
        </button>
      </div>
      {showDetails && (
        <>
          {loading && <p className="checkin-hint">carregando…</p>}
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          {explanation && (
            <div className="explanation">
              <p>{explanation.explanation}</p>
              <ul className="plain-list">
                {explanation.indicators.map((ind) => (
                  <li key={ind.indicator_key}>
                    <strong>{ind.label}</strong>
                    {ind.baseline_mean !== null && ind.recent_value !== null && (
                      <span>
                        {" "}
                        — seu normal {ind.baseline_mean.toFixed(1)}, na época {ind.recent_value.toFixed(1)}
                        {ind.direction && ` (${ind.direction})`}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </li>
  );
}

export function AnalyticsPage() {
  const [days, setDays] = useState(30);
  const [data, setData] = useState<AnalyticsDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getAnalyticsDashboard(days)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (!cancelled) setError(describeError(err, "não foi possível carregar o painel analítico"));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [days]);

  return (
    <div className="trusted-people-page">
      <h1>Painel analítico</h1>
      <p className="checkin-hint">Como seu funcionamento mudou ao longo do tempo, comparado com o seu próprio padrão.</p>

      <div className="weekday-picker">
        {PERIOD_OPTIONS.map((p) => (
          <button
            key={p}
            type="button"
            className={`weekday-option${days === p ? " weekday-option--selected" : ""}`}
            onClick={() => setDays(p)}
          >
            {p} dias
          </button>
        ))}
      </div>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {loading && <p className="checkin-hint">carregando…</p>}

      {data && (
        <>
          <section className="card">
            <h2>Linha do tempo de estado</h2>
            {data.alert_timeline.length === 0 && <p className="checkin-hint">nenhuma mudança de estado no período.</p>}
            <ul className="plain-list">
              {data.alert_timeline.map((entry) => (
                <li key={entry.id}>
                  <strong>{entry.state === "green" ? "verde" : entry.state === "yellow" ? "amarelo" : "vermelho"}</strong> —{" "}
                  {entry.reason_summary} — {formatDate(entry.created_at)}
                  {entry.resolved_at && ` (resolvido em ${formatDate(entry.resolved_at)})`}
                </li>
              ))}
            </ul>
          </section>

          <section className="card">
            <h2>Tendência por indicador</h2>
            {data.indicators.length === 0 && <p className="checkin-hint">dado insuficiente ainda no período.</p>}
            <ul className="plain-list">
              {data.indicators.map((ind) => (
                <li key={ind.indicator_key}>
                  <strong>{ind.label}</strong>
                  {ind.baseline_mean !== null && ind.recent_value !== null && (
                    <span>
                      {" "}
                      — seu normal {ind.baseline_mean.toFixed(1)}, recente {ind.recent_value.toFixed(1)}
                    </span>
                  )}
                  {ind.trend_slope !== null && <span> — tendência: {trendLabel(ind.trend_slope)}</span>}
                  {ind.sample_size !== null && <span> ({ind.sample_size} amostra(s))</span>}
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h2>Linha do tempo de desvio</h2>
            {data.deviation_timeline.length === 0 && <p className="checkin-hint">nenhum desvio detectado no período.</p>}
            {data.deviation_timeline.length > 0 && (
              <ul className="relationship-list">
                {data.deviation_timeline.map((entry) => (
                  <DeviationEventRow key={entry.id} entry={entry} />
                ))}
              </ul>
            )}
          </section>

          <section className="card">
            <h2>Adesão à medicação</h2>
            {data.medication_adherence.adherence_rate === null ? (
              <p>Nenhuma dose agendada no período.</p>
            ) : (
              <p>
                {Math.round(data.medication_adherence.adherence_rate * 100)}% ({data.medication_adherence.taken_count} de{" "}
                {data.medication_adherence.scheduled_count} doses)
              </p>
            )}
          </section>

          <section className="card">
            <h2>Intervenções</h2>
            <p>
              {data.intervention_stats.total} no total — {data.intervention_stats.helped_count} ajudaram,{" "}
              {data.intervention_stats.not_helped_count} não ajudaram, {data.intervention_stats.no_result_count} sem
              resultado registrado.
            </p>
          </section>
        </>
      )}
    </div>
  );
}
