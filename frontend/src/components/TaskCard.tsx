import { useState } from "react";
import { describeError } from "../api/client";
import { cancelTask, completeTask, pauseTask, postponeTask, resumeTask, startTask } from "../api/tasks";
import type { TaskFailureReasonType, TaskPublic } from "../api/types";
import { useNow } from "../hooks/useNow";
import {
  TASK_FAILURE_REASON_LABELS,
  TASK_FAILURE_REASON_ORDER,
  TASK_STATUS_BADGE_VARIANT,
  TASK_STATUS_LABELS,
} from "../labels";
import { useCelebrationStore } from "../store/celebrationStore";
import { taskIcon } from "../taskTemplates";

function formatDate(iso: string | null): string | null {
  if (!iso) return null;
  return new Date(iso).toLocaleDateString("pt-BR");
}

/**
 * Motivo de adiar em UM toque (chips, não `<select>`). O detalhe em
 * texto continua existindo, mas escondido — nunca obrigatório.
 */
function PostponeChips({
  onSubmit,
  onCancel,
}: {
  onSubmit: (reason: TaskFailureReasonType, customText: string) => Promise<boolean>;
  onCancel: () => void;
}) {
  const [busyReason, setBusyReason] = useState<TaskFailureReasonType | null>(null);
  const [customText, setCustomText] = useState("");

  async function choose(reason: TaskFailureReasonType) {
    setBusyReason(reason);
    const saved = await onSubmit(reason, customText.trim());
    if (!saved) setBusyReason(null);
  }

  return (
    <div className="postpone-chips">
      <p className="postpone-chips__title">Por que adiar? Um toque resolve.</p>
      <div className="chip-row" role="group" aria-label="Por que adiar">
        {TASK_FAILURE_REASON_ORDER.map((reason) => (
          <button
            key={reason}
            type="button"
            className="chip-option"
            disabled={busyReason !== null}
            onClick={() => void choose(reason)}
          >
            {busyReason === reason ? "Adiando…" : TASK_FAILURE_REASON_LABELS[reason]}
          </button>
        ))}
      </div>
      <details className="postpone-chips__detail">
        <summary>quero explicar melhor (opcional)</summary>
        <input
          type="text"
          aria-label="Detalhe (opcional)"
          value={customText}
          onChange={(e) => setCustomText(e.target.value)}
          maxLength={500}
          placeholder="escreva antes de tocar no motivo"
        />
      </details>
      <button type="button" className="button button--ghost button--small" onClick={onCancel}>
        Voltar
      </button>
    </div>
  );
}

function ElapsedBar({ task }: { task: TaskPublic }) {
  const now = useNow(15000);
  if (!task.started_at) return null;
  const elapsedMin = Math.max(0, Math.floor((now.getTime() - new Date(task.started_at).getTime()) / 60000));
  const estimate = task.estimated_minutes;
  const fraction = estimate ? Math.min(1, elapsedMin / estimate) : null;
  const over = estimate !== null && elapsedMin > estimate;
  return (
    <div className="task-elapsed" aria-live="off">
      {fraction !== null && (
        <div className="task-elapsed__track">
          <div className={`task-elapsed__fill${over ? " task-elapsed__fill--over" : ""}`} style={{ width: `${fraction * 100}%` }} />
        </div>
      )}
      <span>
        começou há {elapsedMin} min{estimate ? ` · previsto ~${estimate} min` : ""}
        {over && " — tudo bem passar, termine ou pause quando quiser"}
      </span>
    </div>
  );
}

/**
 * Cartão de missão (redesign 2026-09): UMA ação principal grande — a
 * próxima coisa óbvia pro estado atual (Iniciar / Concluir / Retomar)
 * — e o resto como ações secundárias menores. O "primeiro passo"
 * (campo `description`) aparece em destaque: é ele que ajuda a
 * começar. A regra de quais transições são válidas continua morando
 * só no backend (`task_service.py`); aqui só se decide o que mostrar.
 */
export function TaskCard({
  task,
  relationshipLabel,
  onChanged,
  highlight = false,
  compact = false,
}: {
  task: TaskPublic;
  relationshipLabel: string | null;
  onChanged: (task: TaskPublic) => void;
  highlight?: boolean;
  /** Na fila, só a PRIMEIRA missão ganha botão grande — o resto fica discreto pra não competir. */
  compact?: boolean;
}) {
  const [error, setError] = useState<string | null>(null);
  const [acting, setActing] = useState(false);
  const [showPostpone, setShowPostpone] = useState(false);
  const [confirmingCancel, setConfirmingCancel] = useState(false);
  const celebrate = useCelebrationStore((s) => s.celebrate);

  async function run(action: () => Promise<TaskPublic>): Promise<boolean> {
    setActing(true);
    setError(null);
    try {
      const updated = await action();
      if (updated.status === "completed" && task.status !== "completed") celebrate(updated.title);
      onChanged(updated);
      return true;
    } catch (err) {
      setError(describeError(err, "não foi possível atualizar a tarefa"));
      return false;
    } finally {
      setActing(false);
    }
  }

  const isTerminal = task.status === "completed" || task.status === "cancelled";
  const canStart = task.status === "pending" || task.status === "postponed";
  const icon = taskIcon(task);

  return (
    <li
      className={`card relationship-card task-card task-card--${task.status}${compact ? " task-card--compact" : ""}${highlight ? " task-card--highlight" : ""}`}
    >
      <div className="relationship-card__header">
        <div className="task-card__title">
          {icon && (
            <span className="task-card__icon" aria-hidden="true">
              {icon}
            </span>
          )}
          <strong>{task.title}</strong>
        </div>
        <span className={`status-badge status-badge--${TASK_STATUS_BADGE_VARIANT[task.status]}`}>
          {TASK_STATUS_LABELS[task.status]}
        </span>
      </div>

      {task.description && !isTerminal && !compact && (
        <p className="task-card__first-step">
          <span>primeiro passo</span> {task.description}
        </p>
      )}
      {task.description && (isTerminal || compact) && <p className="relationship-card__email">{task.description}</p>}

      <div className="task-card__meta relationship-card__dates">
        {task.estimated_minutes && <span className="meta-pill">⏱ ~{task.estimated_minutes} min</span>}
        {task.priority === "high" && <span className="meta-pill meta-pill--high">importante</span>}
        {task.due_date && <span className="meta-pill">prazo {formatDate(task.due_date)}</span>}
        {task.postponed_count > 0 && <span className="meta-pill">adiada {task.postponed_count}x</span>}
      </div>

      {task.status === "started" && <ElapsedBar task={task} />}

      {task.origin === "trusted_person_suggestion" && (
        <p className="checkin-hint">sugerida por {relationshipLabel ?? "uma pessoa de confiança"}</p>
      )}

      {task.postponed_count >= 2 && !isTerminal && !showPostpone && (
        <p className="task-card__nudge">
          Já adiou {task.postponed_count}x — que tal fazer só o primeiro passo e parar ali? Isso já conta.
        </p>
      )}

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      {!isTerminal && !showPostpone && !confirmingCancel && (
        <div className="task-card__actions">
          {canStart && (
            <button type="button" className={compact ? "button button--ghost" : "button button--big"} onClick={() => void run(() => startTask(task.id))} disabled={acting}>
              Iniciar
            </button>
          )}
          {task.status === "started" && (
            <button type="button" className={compact ? "button button--ghost" : "button button--big"} onClick={() => void run(() => completeTask(task.id))} disabled={acting}>
              Concluir
            </button>
          )}
          {task.status === "paused" && (
            <button type="button" className={compact ? "button button--ghost" : "button button--big"} onClick={() => void run(() => resumeTask(task.id))} disabled={acting}>
              Retomar
            </button>
          )}

          <div className="task-card__secondary">
            {task.status !== "started" && (
              <button type="button" className="button button--ghost button--small" onClick={() => void run(() => completeTask(task.id))} disabled={acting}>
                Concluir
              </button>
            )}
            {task.status === "started" && (
              <button type="button" className="button button--ghost button--small" onClick={() => void run(() => pauseTask(task.id))} disabled={acting}>
                Pausar
              </button>
            )}
            <button type="button" className="button button--ghost button--small" onClick={() => setShowPostpone(true)} disabled={acting}>
              Adiar
            </button>
            <button type="button" className="button button--ghost button--small button--quiet" onClick={() => setConfirmingCancel(true)} disabled={acting}>
              Cancelar tarefa
            </button>
          </div>
        </div>
      )}

      {showPostpone && (
        <PostponeChips
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
          <button type="button" className="button button--danger" onClick={() => void run(() => cancelTask(task.id))} disabled={acting}>
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
