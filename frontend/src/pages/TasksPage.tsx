import { useEffect, useState, type FormEvent } from "react";
import { describeError } from "../api/client";
import {
  cancelTask,
  completeTask,
  createTask,
  listTasks,
  pauseTask,
  postponeTask,
  resumeTask,
  startTask,
} from "../api/tasks";
import { listTrustedPeople } from "../api/trustedPeople";
import type { TaskFailureReasonType, TaskPriority, TaskPublic } from "../api/types";
import {
  TASK_FAILURE_REASON_LABELS,
  TASK_FAILURE_REASON_ORDER,
  TASK_PRIORITY_LABELS,
  TASK_PRIORITY_ORDER,
  TASK_STATUS_BADGE_VARIANT,
  TASK_STATUS_LABELS,
} from "../labels";

function formatDate(iso: string | null): string | null {
  if (!iso) return null;
  return new Date(iso).toLocaleDateString("pt-BR");
}

function CreateTaskForm({ onCreated }: { onCreated: (task: TaskPublic) => void }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<TaskPriority>("medium");
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
        due_date: dueDate || null,
      });
      onCreated(task);
      setTitle("");
      setDescription("");
      setDueDate("");
      setPriority("medium");
    } catch (err) {
      setError(describeError(err, "não foi possível criar a tarefa"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="card">
      <h2>Nova tarefa</h2>
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
          Prioridade
          <select value={priority} onChange={(e) => setPriority(e.target.value as TaskPriority)}>
            {TASK_PRIORITY_ORDER.map((p) => (
              <option key={p} value={p}>
                {TASK_PRIORITY_LABELS[p]}
              </option>
            ))}
          </select>
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
        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Criando…" : "Criar tarefa"}
        </button>
      </form>
    </section>
  );
}

function PostponeForm({
  onSubmit,
  onCancel,
}: {
  onSubmit: (reason: TaskFailureReasonType, customText: string) => Promise<boolean>;
  onCancel: () => void;
}) {
  const [reason, setReason] = useState<TaskFailureReasonType>(TASK_FAILURE_REASON_ORDER[0]);
  const [customText, setCustomText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const saved = await onSubmit(reason, customText.trim());
      if (!saved) setSubmitting(false);
    } catch (err) {
      setError(describeError(err, "não foi possível adiar"));
      setSubmitting(false);
    }
  }

  return (
    <form className="invite-form" onSubmit={handleSubmit}>
      <label>
        Por que adiar
        <select value={reason} onChange={(e) => setReason(e.target.value as TaskFailureReasonType)}>
          {TASK_FAILURE_REASON_ORDER.map((r) => (
            <option key={r} value={r}>
              {TASK_FAILURE_REASON_LABELS[r]}
            </option>
          ))}
        </select>
      </label>
      <label>
        Detalhe (opcional)
        <input type="text" value={customText} onChange={(e) => setCustomText(e.target.value)} maxLength={500} />
      </label>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="relationship-card__actions">
        <button type="submit" className="button button--ghost" disabled={submitting}>
          {submitting ? "Adiando…" : "Confirmar adiamento"}
        </button>
        <button type="button" className="button button--ghost" onClick={onCancel}>
          Cancelar
        </button>
      </div>
    </form>
  );
}

export function TaskCard({
  task,
  relationshipLabel,
  onChanged,
}: {
  task: TaskPublic;
  relationshipLabel: string | null;
  onChanged: (task: TaskPublic) => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [acting, setActing] = useState(false);
  const [showPostpone, setShowPostpone] = useState(false);
  const [confirmingCancel, setConfirmingCancel] = useState(false);

  async function run(action: () => Promise<TaskPublic>): Promise<boolean> {
    setActing(true);
    setError(null);
    try {
      onChanged(await action());
      return true;
    } catch (err) {
      setError(describeError(err, "não foi possível atualizar a tarefa"));
      return false;
    } finally {
      setActing(false);
    }
  }

  const isTerminal = task.status === "completed" || task.status === "cancelled";

  return (
    <li className="card relationship-card">
      <div className="relationship-card__header">
        <div>
          <strong>{task.title}</strong>
          {task.description && <p className="relationship-card__email">{task.description}</p>}
        </div>
        <span className={`status-badge status-badge--${TASK_STATUS_BADGE_VARIANT[task.status]}`}>
          {TASK_STATUS_LABELS[task.status]}
        </span>
      </div>

      <p className="relationship-card__dates">
        prioridade {TASK_PRIORITY_LABELS[task.priority]}
        {task.due_date && ` — prazo ${formatDate(task.due_date)}`}
        {task.postponed_count > 0 && ` — adiada ${task.postponed_count}x`}
      </p>

      {task.origin === "trusted_person_suggestion" && (
        <p className="checkin-hint">sugerida por {relationshipLabel ?? "uma pessoa de confiança"}</p>
      )}

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      {!isTerminal && !showPostpone && (
        <div className="relationship-card__actions">
          {(task.status === "pending" || task.status === "postponed") && (
            <button type="button" className="button button--ghost" onClick={() => void run(() => startTask(task.id))} disabled={acting}>
              Iniciar
            </button>
          )}
          {task.status === "paused" && (
            <button type="button" className="button button--ghost" onClick={() => void run(() => resumeTask(task.id))} disabled={acting}>
              Retomar
            </button>
          )}
          {task.status === "started" && (
            <button type="button" className="button button--ghost" onClick={() => void run(() => pauseTask(task.id))} disabled={acting}>
              Pausar
            </button>
          )}
          <button type="button" className="button button--ghost" onClick={() => setShowPostpone(true)} disabled={acting}>
            Adiar
          </button>
          <button type="button" className="button button--ghost" onClick={() => void run(() => completeTask(task.id))} disabled={acting}>
            Concluir
          </button>
          {!confirmingCancel && (
            <button type="button" className="button button--ghost" onClick={() => setConfirmingCancel(true)} disabled={acting}>
              Cancelar tarefa
            </button>
          )}
        </div>
      )}

      {showPostpone && (
        <PostponeForm
          onCancel={() => setShowPostpone(false)}
          onSubmit={async (reason, customText) => {
            const saved = await run(() => postponeTask(task.id, { reason, custom_text: customText || null }));
            if (saved) setShowPostpone(false);
            return saved;
          }}
        />
      )}

      {confirmingCancel && (
        <div className="relationship-card__revoke">
          <span>Cancelar esta tarefa?</span>
          <button
            type="button"
            className="button button--danger"
            onClick={() => void run(() => cancelTask(task.id))}
            disabled={acting}
          >
            {acting ? "Cancelando…" : "Sim, cancelar"}
          </button>
          <button type="button" className="button button--ghost" onClick={() => setConfirmingCancel(false)}>
            Voltar
          </button>
        </div>
      )}
    </li>
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

  return (
    <div className="trusted-people-page">
      <h1>Tarefas</h1>
      <p className="checkin-hint">
        Inclui tarefas que você criou e as sugeridas por alguém da sua rede de confiança — sugestão nunca começa
        automaticamente, fica pendente até você decidir o que fazer com ela.
      </p>

      <CreateTaskForm onCreated={handleCreated} />

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {tasks === null && !error && <p className="checkin-hint">carregando…</p>}
      {tasks !== null && tasks.length === 0 && <p className="checkin-hint">nenhuma tarefa ainda.</p>}
      {tasks !== null && tasks.length > 0 && (
        <ul className="relationship-list">
          {tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              relationshipLabel={task.source_relationship_id ? relationshipLabels[task.source_relationship_id] ?? null : null}
              onChanged={handleChanged}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

