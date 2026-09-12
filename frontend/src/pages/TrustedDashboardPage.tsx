import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { describeError } from "../api/client";
import {
  acceptInterventionAsTrusted,
  getTrustedDashboard,
  getTrustedPersonalPlan,
  listWatchedAccounts,
  recordObservationAsTrusted,
  suggestTaskAsTrusted,
} from "../api/trustedPeople";
import type {
  InterventionPublic,
  ObservationCategory,
  ObservationIntensity,
  ObservationSince,
  PersonalPlanPublic,
  RelationshipAsTrustedPublic,
  TrustedDashboard,
} from "../api/types";
import { StateBadge } from "../components/StateBadge";
import {
  OBSERVATION_CATEGORY_LABELS,
  OBSERVATION_CATEGORY_ORDER,
  OBSERVATION_INTENSITY_LABELS,
  OBSERVATION_INTENSITY_ORDER,
  OBSERVATION_SINCE_LABELS,
  OBSERVATION_SINCE_ORDER,
} from "../labels";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR");
}

function trendLabel(slope: number | null): string {
  if (slope === null) return "";
  if (slope > 0.01) return "subindo";
  if (slope < -0.01) return "descendo";
  return "estável";
}

function RecordObservationForm({ relationshipId }: { relationshipId: string }) {
  const [category, setCategory] = useState<ObservationCategory>(OBSERVATION_CATEGORY_ORDER[0]);
  const [since, setSince] = useState<ObservationSince>(OBSERVATION_SINCE_ORDER[0]);
  const [intensity, setIntensity] = useState<ObservationIntensity>(OBSERVATION_INTENSITY_ORDER[0]);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccess(false);
    setSubmitting(true);
    try {
      await recordObservationAsTrusted(relationshipId, { category, since, intensity, note: note.trim() || null });
      setNote("");
      setSuccess(true);
    } catch (err) {
      setError(describeError(err, "não foi possível registrar a observação"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="card">
      <h2>Registrar uma observação</h2>
      <p className="checkin-hint">
        Só você e a pessoa observada veem isto — nunca vira um alerta automático sozinho, é informação pra ela olhar.
      </p>
      <form className="invite-form" onSubmit={handleSubmit}>
        <label>
          O que você notou
          <select value={category} onChange={(e) => setCategory(e.target.value as ObservationCategory)}>
            {OBSERVATION_CATEGORY_ORDER.map((key) => (
              <option key={key} value={key}>
                {OBSERVATION_CATEGORY_LABELS[key]}
              </option>
            ))}
          </select>
        </label>
        <label>
          Desde quando
          <select value={since} onChange={(e) => setSince(e.target.value as ObservationSince)}>
            {OBSERVATION_SINCE_ORDER.map((key) => (
              <option key={key} value={key}>
                {OBSERVATION_SINCE_LABELS[key]}
              </option>
            ))}
          </select>
        </label>
        <label>
          Intensidade
          <select value={intensity} onChange={(e) => setIntensity(e.target.value as ObservationIntensity)}>
            {OBSERVATION_INTENSITY_ORDER.map((key) => (
              <option key={key} value={key}>
                {OBSERVATION_INTENSITY_LABELS[key]}
              </option>
            ))}
          </select>
        </label>
        <label>
          Nota (opcional)
          <input type="text" value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {success && <p className="checkin-hint">observação registrada.</p>}
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Registrando…" : "Registrar observação"}
        </button>
      </form>
    </section>
  );
}

function SuggestTaskForm({ relationshipId }: { relationshipId: string }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccess(false);
    setSubmitting(true);
    try {
      await suggestTaskAsTrusted(relationshipId, {
        title: title.trim(),
        description: description.trim() || null,
        due_date: dueDate || null,
      });
      setTitle("");
      setDescription("");
      setDueDate("");
      setSuccess(true);
    } catch (err) {
      setError(describeError(err, "não foi possível sugerir a tarefa"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="card">
      <h2>Sugerir uma tarefa</h2>
      <p className="checkin-hint">
        A tarefa nasce pendente na lista dela — nunca começa sozinha nem é marcada como prioridade automaticamente.
      </p>
      <form className="invite-form" onSubmit={handleSubmit}>
        <label>
          Título
          <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={200} />
        </label>
        <label>
          Descrição (opcional)
          <input type="text" value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
        <label>
          Prazo (opcional)
          <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {success && <p className="checkin-hint">tarefa sugerida.</p>}
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Sugerindo…" : "Sugerir tarefa"}
        </button>
      </form>
    </section>
  );
}

function PendingSupportRequests({
  relationshipId,
  requests,
  onAccepted,
}: {
  relationshipId: string;
  requests: InterventionPublic[];
  onAccepted: (id: string) => void;
}) {
  const [acceptingId, setAcceptingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleAccept(interventionId: string) {
    setAcceptingId(interventionId);
    setError(null);
    try {
      await acceptInterventionAsTrusted(relationshipId, interventionId);
      onAccepted(interventionId);
    } catch (err) {
      setError(describeError(err, "não foi possível aceitar o pedido"));
    } finally {
      setAcceptingId(null);
    }
  }

  if (requests.length === 0) {
    return <p className="checkin-hint">nenhum pedido de acompanhamento no momento.</p>;
  }

  return (
    <>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <ul className="plain-list">
        {requests.map((req) => (
          <li key={req.id}>
            <p>{req.suggestion_text}</p>
            <button
              type="button"
              className="button button--ghost"
              onClick={() => void handleAccept(req.id)}
              disabled={acceptingId === req.id}
            >
              {acceptingId === req.id ? "Aceitando…" : "Aceitar"}
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}

function TrustedPersonalPlanSection({ plan }: { plan: PersonalPlanPublic }) {
  return (
    <section className="card">
      <h2>Plano para quando ela(e) não perceber</h2>
      <p className="checkin-hint">
        Escrito enquanto ela(e) estava estável — o ponto de um plano assim é você já conhecer o conteúdo antes de
        precisar dele.
      </p>
      <h3>{plan.title}</h3>
      <p style={{ whiteSpace: "pre-wrap" }}>{plan.description}</p>
      {plan.rules.length > 0 && (
        <ul className="plain-list">
          {plan.rules.filter((r) => r.is_active).map((r) => (
            <li key={r.id}>{r.threshold_description}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function TrustedDashboardPage() {
  const { relationshipId } = useParams<{ relationshipId: string }>();
  const [relationship, setRelationship] = useState<RelationshipAsTrustedPublic | null | undefined>(undefined);
  const [dashboard, setDashboard] = useState<TrustedDashboard | null | undefined>(undefined);
  const [plan, setPlan] = useState<PersonalPlanPublic | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!relationshipId) return;
    let cancelled = false;

    async function load() {
      try {
        const [accounts, dash] = await Promise.all([listWatchedAccounts(), getTrustedDashboard(relationshipId!)]);
        if (cancelled) return;
        const found = accounts.find((r) => r.id === relationshipId) ?? null;
        setRelationship(found);
        setDashboard(dash);
        const hasCrisisAccess = found?.permissions.some(
          (p) => p.permission_key === "access_crisis_plan" && p.is_granted,
        );
        if (hasCrisisAccess) {
          const fetchedPlan = await getTrustedPersonalPlan(relationshipId!);
          if (!cancelled) setPlan(fetchedPlan);
        }
      } catch (err) {
        if (!cancelled) setError(describeError(err, "não foi possível carregar este painel"));
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [relationshipId]);

  if (!relationshipId) {
    return null;
  }

  const canRecordObservation = relationship?.permissions.some(
    (p) => p.permission_key === "record_observation" && p.is_granted,
  );
  const canSuggestTask = relationship?.permissions.some(
    (p) => p.permission_key === "suggest_task" && p.is_granted,
  );

  return (
    <div className="trusted-people-page">
      <p>
        <Link to="/observando">← voltar pra lista</Link>
      </p>
      <h1>
        {relationship === undefined && "carregando…"}
        {relationship === null && "Relacionamento não encontrado"}
        {relationship && (relationship.relationship_label || relationship.owner_display_name)}
      </h1>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      {dashboard === undefined && !error && <p className="checkin-hint">carregando painel…</p>}

      {dashboard && (
        <>
          <section className="card">
            <h2>Estado</h2>
            {dashboard.state ? (
              <StateBadge state={dashboard.state} reason={dashboard.state_reason ?? ""} />
            ) : (
              <p className="checkin-hint">
                nada calculado ainda, ou esse estado não está visível pra você com as permissões atuais.
              </p>
            )}
          </section>

          {dashboard.medication_adherence && (
            <section className="card">
              <h2>Adesão à medicação (últimos {dashboard.medication_adherence.period_days} dias)</h2>
              {dashboard.medication_adherence.adherence_rate === null ? (
                <p>nenhuma dose agendada no período.</p>
              ) : (
                <p>
                  {Math.round(dashboard.medication_adherence.adherence_rate * 100)}% (
                  {dashboard.medication_adherence.taken_count} de {dashboard.medication_adherence.scheduled_count}{" "}
                  doses) — nunca dose a dose, só a taxa agregada.
                </p>
              )}
            </section>
          )}

          {dashboard.indicators && (
            <section className="card">
              <h2>Indicadores liberados</h2>
              {dashboard.indicators.length === 0 && <p className="checkin-hint">nenhum indicador liberado ainda.</p>}
              <ul className="plain-list">
                {dashboard.indicators.map((ind) => (
                  <li key={ind.indicator_key}>
                    <strong>{ind.label}</strong>
                    {ind.baseline_mean !== null && ind.recent_value !== null && (
                      <span>
                        {" "}
                        — padrão dela(e) {ind.baseline_mean.toFixed(1)}, recente {ind.recent_value.toFixed(1)}
                      </span>
                    )}
                    {ind.trend_slope !== null && <span> — tendência: {trendLabel(ind.trend_slope)}</span>}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {dashboard.alert_timeline && (
            <section className="card">
              <h2>Histórico de estado</h2>
              {dashboard.alert_timeline.length === 0 && <p className="checkin-hint">nenhum registro no histórico.</p>}
              <ul className="plain-list">
                {dashboard.alert_timeline.map((entry) => (
                  <li key={entry.id}>
                    <strong>{entry.state === "green" ? "verde" : entry.state === "yellow" ? "amarelo" : "vermelho"}</strong>{" "}
                    — {entry.reason_summary} — {formatDate(entry.created_at)}
                    {entry.resolved_at && ` (resolvido em ${formatDate(entry.resolved_at)})`}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {dashboard.deviation_timeline && (
            <section className="card">
              <h2>Histórico de desvio</h2>
              {dashboard.deviation_timeline.length === 0 && (
                <p className="checkin-hint">nenhum desvio detectado.</p>
              )}
              <ul className="plain-list">
                {dashboard.deviation_timeline.map((entry) => (
                  <li key={entry.id}>
                    <strong>{entry.engine_label}</strong> — detectado em {formatDate(entry.detected_at)}, há{" "}
                    {entry.duration_days} dia(s)
                  </li>
                ))}
              </ul>
            </section>
          )}

          {dashboard.pending_support_requests && (
            <section className="card">
              <h2>Pedidos de acompanhamento</h2>
              <PendingSupportRequests
                relationshipId={relationshipId}
                requests={dashboard.pending_support_requests}
                onAccepted={(id) =>
                  setDashboard((prev) =>
                    prev
                      ? {
                          ...prev,
                          pending_support_requests: (prev.pending_support_requests ?? []).filter((r) => r.id !== id),
                        }
                      : prev,
                  )
                }
              />
            </section>
          )}

          {plan && <TrustedPersonalPlanSection plan={plan} />}

          {canRecordObservation && <RecordObservationForm relationshipId={relationshipId} />}

          {canSuggestTask && <SuggestTaskForm relationshipId={relationshipId} />}
        </>
      )}
    </div>
  );
}
