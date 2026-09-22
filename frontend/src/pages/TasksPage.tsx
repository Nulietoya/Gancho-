import { useEffect, useState, type FormEvent } from "react";
import { describeError } from "../api/client";
import { createTask, listTasks } from "../api/tasks";
import { listTrustedPeople } from "../api/trustedPeople";
import type { TaskPriority, TaskPublic } from "../api/types";
import { FocusTimer } from "../components/FocusTimer";
import { QuickAddTasks } from "../components/QuickAddTasks";
import { TaskCard } from "../components/TaskCard";
import { TASK_PRIORITY_LABELS, TASK_PRIORITY_ORDER } from "../labels";
import { groupTasks } from "../taskOrdering";

// Mantido exportado daqui porque outras telas (Home) e testes já importavam deste arquivo.
export { TaskCard };

const MINUTE_OPTIONS = [5, 15, 30, 60];

/**
 * Escrever a própria missão continua possível, mas é o caminho
 * secundário: só o título é obrigatório; tempo/prioridade/prazo são
 * chips opcionais escondidos em "mais detalhes".
 */
function CreateTaskForm({ onCreated }: { onCreated: (task: TaskPublic) => void }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<TaskPriority>("medium");
  const [minutes, setMinutes] = useState<number | null>(null);
  const [dueDate, setDueDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const task = await createTask({
        title: title.trim(),
        description: description.trim() || null,
        priority,
        estimated_minutes: minutes,
        due_date: dueDate || null,
      });
      onCreated(task);
      setTitle("");
      setDescription("");
      setDueDate("");
      setMinutes(null);
      setPriority("medium");
    } catch (err) {
      setError(describeError(err, "não foi possível criar a tarefa"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="card">
      <form className="invite-form" onSubmit={handleSubmit}>
        <label>
          Título
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            maxLength={200}
            placeholder="ex.: responder o e-mail da faculdade"
          />
        </label>
        <label>
          Primeiro passo (opcional)
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="a menor ação possível pra começar"
          />
        </label>
        <div className="chip-field">
          <span>Quanto tempo mais ou menos?</span>
          <div className="chip-row" role="group" aria-label="Tempo estimado">
            {MINUTE_OPTIONS.map((m) => (
              <button
                key={m}
                type="button"
                className={`chip-option${minutes === m ? " chip-option--selected" : ""}`}
                aria-pressed={minutes === m}
                onClick={() => setMinutes(minutes === m ? null : m)}
              >
                {m < 60 ? `${m} min` : "1 h+"}
              </button>
            ))}
          </div>
        </div>
        <div className="chip-field">
          <span>Prioridade</span>
          <div className="chip-row" role="group" aria-label="Prioridade">
            {TASK_PRIORITY_ORDER.map((p) => (
              <button
                key={p}
                type="button"
                className={`chip-option${priority === p ? " chip-option--selected" : ""}`}
                aria-pressed={priority === p}
                onClick={() => setPriority(p)}
              >
                {TASK_PRIORITY_LABELS[p]}
              </button>
            ))}
          </div>
        </div>
        <label>
          Prazo (opcional)
          <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Criando…" : "Criar tarefa"}
        </button>
      </form>
    </section>
  );
}

export function TasksPage() {
  const [tasks, setTasks] = useState<TaskPublic[] | null>(null);
  const [relationshipLabels, setRelationshipLabels] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([listTasks(), listTrustedPeople()])
      .then(([taskList, relationships]) => {
        if (cancelled) return;
        setTasks(taskList);
        const labels: Record<string, string> = {};
        for (const r of relationships) {
          labels[r.id] = r.relationship_label || r.invite_email;
        }
        setRelationshipLabels(labels);
      })
      .catch((err) => {
        if (!cancelled) setError(describeError(err, "não foi possível carregar suas tarefas"));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function handleChanged(updated: TaskPublic) {
    setTasks((prev) => (prev ?? []).map((t) => (t.id === updated.id ? updated : t)));
  }

  function handleCreated(task: TaskPublic) {
    setTasks((prev) => [task, ...(prev ?? [])]);
  }

  const groups = groupTasks(tasks ?? []);
  const doneToday = groups.doneToday.length;
  const totalToday = doneToday + groups.now.length + groups.queue.length;

  function renderList(list: TaskPublic[], compactAfterFirst = false) {
    return (
      <ul className="relationship-list">
        {list.map((task, index) => (
          <TaskCard
            key={task.id}
            compact={compactAfterFirst && (index > 0 || groups.now.length > 0)}
            task={task}
            relationshipLabel={task.source_relationship_id ? relationshipLabels[task.source_relationship_id] ?? null : null}
            onChanged={handleChanged}
          />
        ))}
      </ul>
    );
  }

  const quickAdd = <QuickAddTasks tasks={tasks} onCreated={handleCreated} />;
  const isEmpty = tasks !== null && groups.now.length === 0 && groups.queue.length === 0;

  return (
    <div className="trusted-people-page tasks-page">
      <header className="tasks-page__header">
        <h1>Missões</h1>
        {tasks !== null && totalToday > 0 && (
          <div className="day-progress" aria-label={`${doneToday} de ${totalToday} feitas hoje`}>
            <div className="day-progress__track">
              <div className="day-progress__fill" style={{ width: `${(doneToday / totalToday) * 100}%` }} />
            </div>
            <span>
              <strong>{doneToday}</strong> de {totalToday} feitas hoje
            </span>
          </div>
        )}
      </header>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {tasks === null && !error && <p className="checkin-hint">carregando…</p>}

      {isEmpty && (
        <p className="empty-hint">
          Lista vazia. Não precisa pensar em nada — escolhe um cartão aí embaixo, ou um pacote pronto.
        </p>
      )}
      {isEmpty && quickAdd}

      {groups.now.length > 0 && (
        <section className="task-group">
          <h2 className="task-group__title">Fazendo agora</h2>
          {renderList(groups.now)}
        </section>
      )}

      {groups.queue.length > 0 && (
        <section className="task-group">
          <h2 className="task-group__title">
            Na fila <span className="task-group__count">{groups.queue.length}</span>
          </h2>
          {groups.queue.length > 5 && (
            <p className="checkin-hint">Muita coisa? Olha só a primeira. O resto espera.</p>
          )}
          {renderList(groups.queue, true)}
        </section>
      )}

      {!isEmpty && tasks !== null && quickAdd}

      <details className="home-more">
        <summary>Escrever a minha</summary>
        <div className="home-more__content">
          <CreateTaskForm onCreated={handleCreated} />
        </div>
      </details>

      <details className="home-more">
        <summary>Timer visual</summary>
        <div className="home-more__content">
          <FocusTimer />
        </div>
      </details>

      {groups.doneToday.length > 0 && (
        <section className="task-group task-group--done">
          <h2 className="task-group__title">Feitas hoje ✓</h2>
          {renderList(groups.doneToday)}
        </section>
      )}

      {groups.archive.length > 0 && (
        <details className="home-more">
          <summary>Antigas e canceladas ({groups.archive.length})</summary>
          <div className="home-more__content">{renderList(groups.archive)}</div>
        </details>
      )}
    </div>
  );
}
