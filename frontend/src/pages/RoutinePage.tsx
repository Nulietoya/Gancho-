import { useEffect, useState, type FormEvent } from "react";
import { describeError } from "../api/client";
import { createLifeEvent, createRoutine, getCurrentRoutine, listLifeEvents, startNewRoutineVersion, updateRoutine } from "../api/routines";
import type { ActivationDomain, LifeEventPublic, LifeEventType, RoutineFields, RoutinePublic } from "../api/types";
import { RoutineForm } from "../components/RoutineForm";
import { ACTIVATION_DOMAIN_LABELS, LIFE_EVENT_TYPE_LABELS } from "../labels";

const EMPTY_FIELDS: RoutineFields = {
  typical_wake_time: null,
  typical_sleep_time: null,
  goes_out_on_weekdays: null,
  social_contact_days_per_week: null,
  typical_tasks_postponed_on_good_day: null,
  selected_activation_domains: null,
  notes: null,
};

function RoutineSummary({ routine }: { routine: RoutinePublic }) {
  return (
    <ul className="plain-list">
      <li>Versão {routine.version} — desde {new Date(routine.period_start).toLocaleDateString("pt-BR")}</li>
      {routine.typical_wake_time && <li>Acorda por volta de {routine.typical_wake_time.slice(0, 5)}</li>}
      {routine.typical_sleep_time && <li>Dorme por volta de {routine.typical_sleep_time.slice(0, 5)}</li>}
      {routine.goes_out_on_weekdays !== null && (
        <li>{routine.goes_out_on_weekdays ? "Costuma sair de casa em dias de semana" : "Não costuma sair de casa em dias de semana"}</li>
      )}
      {routine.social_contact_days_per_week !== null && (
        <li>{routine.social_contact_days_per_week} dia(s) de contato social por semana</li>
      )}
      {routine.typical_tasks_postponed_on_good_day !== null && (
        <li>{routine.typical_tasks_postponed_on_good_day} tarefa(s) adiada(s) mesmo num dia bom</li>
      )}
      {routine.selected_activation_domains && routine.selected_activation_domains.length > 0 && (
        <li>
          Faz parte do dia:{" "}
          {routine.selected_activation_domains
            .map((d) => ACTIVATION_DOMAIN_LABELS[d as keyof typeof ACTIVATION_DOMAIN_LABELS] ?? d)
            .join(", ")}
        </li>
      )}
      {routine.notes && <li>{routine.notes}</li>}
    </ul>
  );
}

function LifeEventsSection() {
  const [events, setEvents] = useState<LifeEventPublic[] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [eventType, setEventType] = useState<LifeEventType>("other");
  const [description, setDescription] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listLifeEvents()
      .then((result) => {
        if (!cancelled) setEvents(result);
      })
      .catch(() => {
        if (!cancelled) setEvents([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const created = await createLifeEvent({
        event_type: eventType,
        description: description.trim() || null,
        start_date: startDate,
        end_date: endDate || null,
      });
      setEvents((prev) => [created, ...(prev ?? [])]);
      setShowForm(false);
      setDescription("");
      setStartDate("");
      setEndDate("");
    } catch (err) {
      setError(describeError(err, "não foi possível registrar o evento"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="card">
      <h2>Eventos de vida</h2>
      <p className="checkin-hint">
        Viagem, novo emprego, doença, mudança — contexto que evita confundir uma transição de vida com uma
        deterioração de verdade.
      </p>

      {events === null && <p className="checkin-hint">carregando…</p>}
      {events !== null && events.length === 0 && !showForm && (
        <p className="checkin-hint">nenhum evento registrado ainda.</p>
      )}
      {events !== null && events.length > 0 && (
        <ul className="plain-list">
          {events.map((e) => (
            <li key={e.id}>
              <strong>{LIFE_EVENT_TYPE_LABELS[e.event_type]}</strong> — desde{" "}
              {new Date(e.start_date).toLocaleDateString("pt-BR")}
              {e.end_date && ` até ${new Date(e.end_date).toLocaleDateString("pt-BR")}`}
              {e.description && ` — ${e.description}`}
            </li>
          ))}
        </ul>
      )}

      {!showForm && (
        <button type="button" className="button button--ghost" onClick={() => setShowForm(true)}>
          Registrar evento
        </button>
      )}

      {showForm && (
        <form className="invite-form" onSubmit={handleSubmit}>
          <label>
            Tipo
            <select value={eventType} onChange={(e) => setEventType(e.target.value as LifeEventType)}>
              {Object.entries(LIFE_EVENT_TYPE_LABELS).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Início
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
          </label>
          <label>
            Fim (opcional)
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </label>
          <label>
            Descrição (opcional)
            <input type="text" value={description} onChange={(e) => setDescription(e.target.value)} maxLength={500} />
          </label>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <div className="relationship-card__actions">
            <button type="submit" className="button" disabled={submitting}>
              {submitting ? "Salvando…" : "Registrar"}
            </button>
            <button type="button" className="button button--ghost" onClick={() => setShowForm(false)}>
              Cancelar
            </button>
          </div>
        </form>
      )}
    </section>
  );
}

export function RoutinePage() {
  const [routine, setRoutine] = useState<RoutinePublic | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [startingNewVersion, setStartingNewVersion] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getCurrentRoutine()
      .then((result) => {
        if (!cancelled) setRoutine(result);
      })
      .catch((err) => {
        if (!cancelled) setError(describeError(err, "não foi possível carregar sua rotina"));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="trusted-people-page">
      <h1>Rotina de referência</h1>
      <p className="checkin-hint">Como é o seu dia quando você está bem — a base de comparação do seu baseline.</p>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      {routine === undefined && !error && <p className="checkin-hint">carregando…</p>}

      {routine === null && (
        <section className="card">
          <h2>Você ainda não declarou sua rotina</h2>
          <RoutineForm
            initial={EMPTY_FIELDS}
            submitLabel="Salvar rotina"
            onSubmit={async (fields) => {
              const created = await createRoutine(fields);
              setRoutine(created);
            }}
          />
        </section>
      )}

      {routine && !editing && !startingNewVersion && (
        <section className="card">
          <h2>Sua rotina atual</h2>
          <RoutineSummary routine={routine} />
          <div className="relationship-card__actions">
            <button type="button" className="button button--ghost" onClick={() => setEditing(true)}>
              Editar
            </button>
            <button type="button" className="button button--ghost" onClick={() => setStartingNewVersion(true)}>
              Começar nova versão (virada de vida)
            </button>
          </div>
        </section>
      )}

      {routine && editing && (
        <section className="card">
          <h2>Editar rotina</h2>
          <RoutineForm
            initial={{ ...routine, selected_activation_domains: routine.selected_activation_domains as ActivationDomain[] | null }}
            submitLabel="Salvar alterações"
            onSubmit={async (fields) => {
              const updated = await updateRoutine(fields);
              setRoutine(updated);
              setEditing(false);
            }}
          />
          <button type="button" className="button button--ghost" onClick={() => setEditing(false)}>
            Cancelar
          </button>
        </section>
      )}

      {routine && startingNewVersion && (
        <section className="card">
          <h2>Nova versão da rotina</h2>
          <p className="checkin-hint">
            Isso fecha a rotina atual e começa uma nova do zero — use quando algo mudou de verdade na sua vida
            (novo emprego, mudança de cidade), não pra um ajuste pontual.
          </p>
          <RoutineForm
            initial={EMPTY_FIELDS}
            submitLabel="Começar nova versão"
            onSubmit={async (fields) => {
              const created = await startNewRoutineVersion(fields);
              setRoutine(created);
              setStartingNewVersion(false);
            }}
          />
          <button type="button" className="button button--ghost" onClick={() => setStartingNewVersion(false)}>
            Cancelar
          </button>
        </section>
      )}

      <LifeEventsSection />
    </div>
  );
}
