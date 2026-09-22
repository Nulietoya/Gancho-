import { useState } from "react";
import { describeError } from "../api/client";
import { createTask, startTask } from "../api/tasks";
import type { TaskPublic } from "../api/types";
import {
  CATEGORY_META,
  ENERGY_META,
  busyTaskTitles,
  suggestTemplates,
  templateToTaskCreate,
  type Energy,
} from "../taskTemplates";

/**
 * "Me dá uma" — pra quando a pessoa nem sabe o que fazer. Mostra UMA
 * sugestão (nunca uma lista pra escolher: escolher também custa), que
 * cabe na energia informada no chip "Como você está funcionando".
 * "Fazer agora" cria e já inicia a missão num toque só.
 */
export function SuggestNow({
  tasks,
  energy,
  onCreated,
}: {
  tasks: TaskPublic[] | null;
  energy: Energy | null;
  onCreated: (task: TaskPublic) => void;
}) {
  const [seed, setSeed] = useState(0);
  const [busy, setBusy] = useState<"now" | "list" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const suggestion = suggestTemplates(energy, busyTaskTitles(tasks), seed)[0];
  if (!suggestion) return null;

  async function add(startNow: boolean) {
    setBusy(startNow ? "now" : "list");
    setError(null);
    try {
      let task = await createTask(templateToTaskCreate(suggestion));
      if (startNow) task = await startTask(task.id);
      onCreated(task);
      setSeed((s) => s + 1);
    } catch (err) {
      setError(describeError(err, "não foi possível adicionar"));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="card suggest-now" aria-labelledby="suggest-now-title">
      <p className="suggest-now__eyebrow" id="suggest-now-title">
        {energy ? `Cabe no seu momento (${ENERGY_META[energy].short})` : "Sugestão pra agora"}
      </p>
      <div className="suggest-now__body" key={suggestion.id}>
        <span className="suggest-now__icon" aria-hidden="true">
          {CATEGORY_META[suggestion.category].icon}
        </span>
        <div>
          <strong className="suggest-now__title">{suggestion.title}</strong>
          <p className="suggest-now__step">
            {suggestion.firstStep} <span>· {suggestion.minutes} min</span>
          </p>
        </div>
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="task-card__actions">
        <button type="button" className="button button--big" onClick={() => void add(true)} disabled={busy !== null}>
          {busy === "now" ? "Começando…" : "Fazer agora"}
        </button>
        <div className="task-card__secondary">
          <button type="button" className="button button--ghost button--small" onClick={() => void add(false)} disabled={busy !== null}>
            {busy === "list" ? "Adicionando…" : "Pôr na lista"}
          </button>
          <button type="button" className="button button--ghost button--small" onClick={() => setSeed((s) => s + 1)} disabled={busy !== null}>
            Outra
          </button>
        </div>
      </div>
    </section>
  );
}
