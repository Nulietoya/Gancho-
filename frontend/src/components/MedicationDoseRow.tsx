import { useState } from "react";
import { createMedicationEvent } from "../api/medications";
import { describeError } from "../api/client";
import type { MedicationDoseToday, MedicationEventStatus, MedicationSkipReason } from "../api/types";
import { MEDICATION_SKIP_REASON_LABELS, MEDICATION_STATUS_LABELS } from "../labels";

const SKIP_STATUSES: { status: MedicationEventStatus; label: string }[] = [
  { status: "not_taken", label: "Não tomei" },
  { status: "skipped_deliberately", label: "Pulei de propósito" },
  { status: "unavailable", label: "Não tinha disponível" },
];

const SKIP_REASONS: MedicationSkipReason[] = [
  "esqueci",
  "rotina_mudou",
  "nao_consegui_levantar",
  "efeito_adverso",
  "medo",
  "medicamento_indisponivel",
  "decisao_propria",
  "outro",
];

function todayScheduledFor(timeOfDay: string): string {
  const today = new Date();
  const y = today.getFullYear();
  const m = String(today.getMonth() + 1).padStart(2, "0");
  const d = String(today.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}T${timeOfDay}`;
}

export function MedicationDoseRow({
  dose,
  onConfirmed,
}: {
  dose: MedicationDoseToday;
  onConfirmed: (scheduleId: string, status: MedicationEventStatus) => void;
}) {
  const [pendingStatus, setPendingStatus] = useState<MedicationEventStatus | null>(null);
  const [reason, setReason] = useState<MedicationSkipReason | "">("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirm(status: MedicationEventStatus, skipReason: MedicationSkipReason | null) {
    setSaving(true);
    setError(null);
    try {
      await createMedicationEvent(dose.medication_id, dose.schedule_id, {
        scheduled_for: todayScheduledFor(dose.time_of_day),
        status,
        skip_reason: skipReason,
      });
      onConfirmed(dose.schedule_id, status);
    } catch (err) {
      setError(describeError(err, "não foi possível registrar"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <li className="dose-row">
      <div className="dose-row__main">
        <strong>{dose.medication_name}</strong> — {dose.time_of_day.slice(0, 5)} —{" "}
        {dose.status ? MEDICATION_STATUS_LABELS[dose.status] : "ainda sem registro"}
      </div>

      {!dose.status && !pendingStatus && (
        <div className="dose-row__actions">
          <button type="button" className="button" onClick={() => void confirm("taken", null)} disabled={saving}>
            Tomei
          </button>
          {SKIP_STATUSES.map(({ status, label }) => (
            <button
              key={status}
              type="button"
              className="button button--ghost"
              onClick={() => setPendingStatus(status)}
              disabled={saving}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {pendingStatus && (
        <div className="dose-row__reason">
          <label>
            Por quê?
            <select value={reason} onChange={(e) => setReason(e.target.value as MedicationSkipReason)}>
              <option value="" disabled>
                selecione um motivo
              </option>
              {SKIP_REASONS.map((r) => (
                <option key={r} value={r}>
                  {MEDICATION_SKIP_REASON_LABELS[r]}
                </option>
              ))}
            </select>
          </label>
          <div className="dose-row__actions">
            <button
              type="button"
              className="button"
              disabled={!reason || saving}
              onClick={() => reason && void confirm(pendingStatus, reason)}
            >
              {saving ? "Salvando…" : "Confirmar"}
            </button>
            <button type="button" className="button button--ghost" onClick={() => setPendingStatus(null)}>
              Cancelar
            </button>
          </div>
        </div>
      )}

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </li>
  );
}
