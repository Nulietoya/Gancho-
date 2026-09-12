import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { submitCheckin } from "../api/checkins";
import { describeError } from "../api/client";

type ScaleFieldKey =
  | "mood"
  | "energy"
  | "anxiety"
  | "ability_to_start_tasks"
  | "willingness_to_interact"
  | "sleep_quality"
  | "sense_of_functioning";

type FormState = Record<ScaleFieldKey, number | null>;

const EMPTY_FORM: FormState = {
  mood: null,
  energy: null,
  anxiety: null,
  ability_to_start_tasks: null,
  willingness_to_interact: null,
  sleep_quality: null,
  sense_of_functioning: null,
};

const FIELDS: { key: ScaleFieldKey; label: string }[] = [
  { key: "mood", label: "Humor" },
  { key: "energy", label: "Energia" },
  { key: "anxiety", label: "Ansiedade" },
  { key: "ability_to_start_tasks", label: "Facilidade de começar tarefas" },
  { key: "willingness_to_interact", label: "Vontade de interagir com outras pessoas" },
  { key: "sleep_quality", label: "Qualidade do sono" },
  { key: "sense_of_functioning", label: "Sensação geral de funcionamento" },
];

export function CheckinPage() {
  const navigate = useNavigate();
  const [values, setValues] = useState<FormState>(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  function setField(key: ScaleFieldKey, value: number) {
    setValues((prev) => ({ ...prev, [key]: prev[key] === value ? null : value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    const hasAnyValue = Object.values(values).some((value) => value !== null);
    if (!hasAnyValue) {
      setError("preencha pelo menos um indicador");
      return;
    }

    setSubmitting(true);
    try {
      await submitCheckin(values);
      setDone(true);
      setTimeout(() => navigate("/", { replace: true }), 1200);
    } catch (err) {
      setError(describeError(err, "não foi possível salvar o check-in"));
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return <p className="page-loading">Check-in salvo. Voltando pro seu painel…</p>;
  }

  return (
    <div className="checkin-page">
      <h1>Como você está hoje?</h1>
      <p className="checkin-hint">Preencha só o que fizer sentido — nada aqui é obrigatório.</p>
      <form onSubmit={handleSubmit}>
        {FIELDS.map(({ key, label }) => (
          <fieldset className="scale-field" key={key}>
            <legend>{label}</legend>
            <div className="scale-options">
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  type="button"
                  key={n}
                  className={`scale-option${values[key] === n ? " scale-option--selected" : ""}`}
                  onClick={() => setField(key, n)}
                  aria-pressed={values[key] === n}
                >
                  {n}
                </button>
              ))}
            </div>
          </fieldset>
        ))}
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Salvando…" : "Salvar check-in"}
        </button>
      </form>
    </div>
  );
}
