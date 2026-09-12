import { useState, type FormEvent } from "react";
import { describeError } from "../api/client";
import type { ActivationDomain, RoutineFields } from "../api/types";
import { ACTIVATION_DOMAIN_LABELS, ACTIVATION_DOMAIN_ORDER } from "../labels";

function toFormBoolean(value: boolean | null | undefined): "sim" | "nao" | "" {
  if (value === true) return "sim";
  if (value === false) return "nao";
  return "";
}

function fromFormBoolean(value: string): boolean | null {
  if (value === "sim") return true;
  if (value === "nao") return false;
  return null;
}

export function RoutineForm({
  initial,
  submitLabel,
  onSubmit,
}: {
  initial: RoutineFields;
  submitLabel: string;
  onSubmit: (fields: RoutineFields) => Promise<void>;
}) {
  const [wakeTime, setWakeTime] = useState(initial.typical_wake_time?.slice(0, 5) ?? "");
  const [sleepTime, setSleepTime] = useState(initial.typical_sleep_time?.slice(0, 5) ?? "");
  const [goesOut, setGoesOut] = useState(toFormBoolean(initial.goes_out_on_weekdays));
  const [socialDays, setSocialDays] = useState(
    initial.social_contact_days_per_week != null ? String(initial.social_contact_days_per_week) : "",
  );
  const [postponedTasks, setPostponedTasks] = useState(
    initial.typical_tasks_postponed_on_good_day != null ? String(initial.typical_tasks_postponed_on_good_day) : "",
  );
  const [domains, setDomains] = useState<ActivationDomain[]>(
    (initial.selected_activation_domains as ActivationDomain[] | null) ?? [],
  );
  const [notes, setNotes] = useState(initial.notes ?? "");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function toggleDomain(domain: ActivationDomain) {
    setDomains((prev) => (prev.includes(domain) ? prev.filter((d) => d !== domain) : [...prev, domain]));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        typical_wake_time: wakeTime ? `${wakeTime}:00` : null,
        typical_sleep_time: sleepTime ? `${sleepTime}:00` : null,
        goes_out_on_weekdays: fromFormBoolean(goesOut),
        social_contact_days_per_week: socialDays === "" ? null : Number(socialDays),
        typical_tasks_postponed_on_good_day: postponedTasks === "" ? null : Number(postponedTasks),
        selected_activation_domains: domains.length > 0 ? domains : null,
        notes: notes.trim() || null,
      });
    } catch (err) {
      setError(describeError(err, "não foi possível salvar a rotina"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="invite-form" onSubmit={handleSubmit}>
      <p className="checkin-hint">Preencha só o que fizer sentido — nada aqui é obrigatório.</p>
      <label>
        Horário que costuma acordar
        <input type="time" value={wakeTime} onChange={(e) => setWakeTime(e.target.value)} />
      </label>
      <label>
        Horário que costuma dormir
        <input type="time" value={sleepTime} onChange={(e) => setSleepTime(e.target.value)} />
      </label>
      <label>
        Costuma sair de casa em dias de semana?
        <select value={goesOut} onChange={(e) => setGoesOut(e.target.value as "sim" | "nao" | "")}>
          <option value="">não informado</option>
          <option value="sim">sim</option>
          <option value="nao">não</option>
        </select>
      </label>
      <label>
        Dias de contato social por semana
        <input
          type="number"
          min={0}
          max={7}
          value={socialDays}
          onChange={(e) => setSocialDays(e.target.value)}
        />
      </label>
      <label>
        Tarefas que costuma adiar mesmo num dia bom
        <input type="number" min={0} value={postponedTasks} onChange={(e) => setPostponedTasks(e.target.value)} />
      </label>
      <fieldset className="scale-field">
        <legend>O que faz parte do seu dia (marque o que se aplica)</legend>
        <div className="indicator-scope" style={{ marginLeft: 0 }}>
          {ACTIVATION_DOMAIN_ORDER.map((domain) => (
            <label key={domain} className="indicator-checkbox">
              <input type="checkbox" checked={domains.includes(domain)} onChange={() => toggleDomain(domain)} />
              {ACTIVATION_DOMAIN_LABELS[domain]}
            </label>
          ))}
        </div>
      </fieldset>
      <label>
        Anotações (opcional)
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
      </label>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <button type="submit" className="button" disabled={submitting}>
        {submitting ? "Salvando…" : submitLabel}
      </button>
    </form>
  );
}
