import { useEffect, useState, type FormEvent } from "react";
import { describeError } from "../api/client";
import { createMedication, createSchedule, discontinueMedication, listMedications, listSchedules } from "../api/medications";
import type { MedicationPublic, SchedulePublic } from "../api/types";

const WEEKDAY_LABELS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"];

function formatWeekdays(weekdays: number[] | null): string {
  if (!weekdays || weekdays.length === 0) return "todo dia";
  return weekdays
    .slice()
    .sort((a, b) => a - b)
    .map((d) => WEEKDAY_LABELS[d])
    .join(", ");
}

function CreateMedicationForm({ onCreated }: { onCreated: (medication: MedicationPublic) => void }) {
  const [name, setName] = useState("");
  const [dosageNote, setDosageNote] = useState("");
  const [notes, setNotes] = useState("");
  const [reminderEnabled, setReminderEnabled] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const medication = await createMedication({
        name,
        dosage_note: dosageNote.trim() || null,
        notes: notes.trim() || null,
        reminder_enabled: reminderEnabled,
      });
      onCreated(medication);
      setName("");
      setDosageNote("");
      setNotes("");
      setReminderEnabled(true);
    } catch (err) {
      setError(describeError(err, "não foi possível adicionar o medicamento"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="card">
      <h2>Adicionar medicamento</h2>
      <form className="invite-form" onSubmit={handleSubmit}>
        <label>
          Nome
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} required maxLength={150} />
        </label>
        <label>
          Como tomar (opcional)
          <input
            type="text"
            value={dosageNote}
            onChange={(e) => setDosageNote(e.target.value)}
            placeholder="ex.: 1 comprimido, com água"
            maxLength={500}
          />
        </label>
        <label>
          Anotações (opcional)
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} />
        </label>
        <label className="permission-checkbox">
          <input type="checkbox" checked={reminderEnabled} onChange={(e) => setReminderEnabled(e.target.checked)} />
          Me lembrar nos horários cadastrados
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Adicionando…" : "Adicionar"}
        </button>
      </form>
    </section>
  );
}

function AddScheduleForm({
  medicationId,
  onCreated,
}: {
  medicationId: string;
  onCreated: (schedule: SchedulePublic) => void;
}) {
  const [timeOfDay, setTimeOfDay] = useState("08:00");
  const [selectedDays, setSelectedDays] = useState<number[]>([]);
  const [everyDay, setEveryDay] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function toggleDay(day: number) {
    setSelectedDays((prev) => (prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const schedule = await createSchedule(medicationId, {
        time_of_day: `${timeOfDay}:00`,
        weekdays: everyDay ? null : selectedDays,
      });
      onCreated(schedule);
      setTimeOfDay("08:00");
      setSelectedDays([]);
      setEveryDay(true);
    } catch (err) {
      setError(describeError(err, "não foi possível adicionar o horário"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="schedule-form" onSubmit={handleSubmit}>
      <label>
        Horário
        <input type="time" value={timeOfDay} onChange={(e) => setTimeOfDay(e.target.value)} required />
      </label>
      <label className="permission-checkbox">
        <input type="checkbox" checked={everyDay} onChange={(e) => setEveryDay(e.target.checked)} />
        Todo dia
      </label>
      {!everyDay && (
        <div className="weekday-picker">
          {WEEKDAY_LABELS.map((label, day) => (
            <button
              key={day}
              type="button"
              className={`weekday-option${selectedDays.includes(day) ? " weekday-option--selected" : ""}`}
              onClick={() => toggleDay(day)}
            >
              {label}
            </button>
          ))}
        </div>
      )}
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <button type="submit" className="button button--ghost" disabled={submitting || (!everyDay && selectedDays.length === 0)}>
        {submitting ? "Adicionando…" : "Adicionar horário"}
      </button>
    </form>
  );
}

function MedicationCard({
  medication,
  onDiscontinued,
}: {
  medication: MedicationPublic;
  onDiscontinued: (medication: MedicationPublic) => void;
}) {
  const [schedules, setSchedules] = useState<SchedulePublic[] | null>(null);
  const [showAddSchedule, setShowAddSchedule] = useState(false);
  const [confirmingDiscontinue, setConfirmingDiscontinue] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listSchedules(medication.id)
      .then((result) => {
        if (!cancelled) setSchedules(result);
      })
      .catch(() => {
        if (!cancelled) setSchedules([]);
      });
    return () => {
      cancelled = true;
    };
  }, [medication.id]);

  async function handleDiscontinue() {
    try {
      const updated = await discontinueMedication(medication.id);
      onDiscontinued(updated);
    } catch (err) {
      setError(describeError(err, "não foi possível descontinuar"));
    } finally {
      setConfirmingDiscontinue(false);
    }
  }

  return (
    <li className="card relationship-card">
      <div className="relationship-card__header">
        <div>
          <strong>{medication.name}</strong>
          {medication.dosage_note && <p className="relationship-card__email">{medication.dosage_note}</p>}
        </div>
        {medication.discontinued_at && <span className="status-badge status-badge--revoked">Descontinuado</span>}
      </div>

      {medication.notes && <p className="checkin-hint">{medication.notes}</p>}

      {!medication.discontinued_at && (
        <>
          <ul className="plain-list">
            {schedules === null && <li className="checkin-hint">carregando horários…</li>}
            {schedules !== null && schedules.length === 0 && (
              <li className="checkin-hint">nenhum horário cadastrado ainda.</li>
            )}
            {schedules?.map((s) => (
              <li key={s.id}>
                {s.time_of_day.slice(0, 5)} — {formatWeekdays(s.weekdays)}
              </li>
            ))}
          </ul>

          <div className="relationship-card__actions">
            <button type="button" className="button button--ghost" onClick={() => setShowAddSchedule((v) => !v)}>
              {showAddSchedule ? "Ocultar" : "Adicionar horário"}
            </button>
          </div>

          {showAddSchedule && (
            <AddScheduleForm
              medicationId={medication.id}
              onCreated={(s) => {
                setSchedules((prev) => [...(prev ?? []), s]);
                setShowAddSchedule(false);
              }}
            />
          )}

          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}

          <div className="relationship-card__revoke">
            {confirmingDiscontinue ? (
              <>
                <span>Descontinuar este medicamento?</span>
                <button type="button" className="button button--danger" onClick={() => void handleDiscontinue()}>
                  Sim, descontinuar
                </button>
                <button type="button" className="button button--ghost" onClick={() => setConfirmingDiscontinue(false)}>
                  Cancelar
                </button>
              </>
            ) : (
              <button type="button" className="button button--ghost" onClick={() => setConfirmingDiscontinue(true)}>
                Descontinuar
              </button>
            )}
          </div>
        </>
      )}
    </li>
  );
}

export function MedicationsPage() {
  const [medications, setMedications] = useState<MedicationPublic[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listMedications()
      .then((result) => {
        if (!cancelled) setMedications(result);
      })
      .catch((err) => {
        if (!cancelled) setError(describeError(err, "não foi possível carregar seus medicamentos"));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function handleCreated(medication: MedicationPublic) {
    setMedications((prev) => [medication, ...(prev ?? [])]);
  }

  function handleDiscontinued(updated: MedicationPublic) {
    setMedications((prev) => (prev ?? []).map((m) => (m.id === updated.id ? updated : m)));
  }

  return (
    <div className="trusted-people-page">
      <h1>Medicamentos</h1>
      <p className="checkin-hint">
        Cadastre seus medicamentos e horários. Isso é só sobre o que você toma e quando — nunca uma instrução
        médica de dose.
      </p>

      <CreateMedicationForm onCreated={handleCreated} />

      <section>
        <h2>Seus medicamentos</h2>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {medications === null && !error && <p className="checkin-hint">carregando…</p>}
        {medications !== null && medications.length === 0 && (
          <p className="checkin-hint">nenhum medicamento cadastrado ainda.</p>
        )}
        {medications !== null && medications.length > 0 && (
          <ul className="relationship-list">
            {medications.map((m) => (
              <MedicationCard key={m.id} medication={m} onDiscontinued={handleDiscontinued} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
