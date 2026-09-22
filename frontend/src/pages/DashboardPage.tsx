import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listCheckins, submitCheckin, updateCheckin } from "../api/checkins";
import { describeError } from "../api/client";
import { getDailyDashboard } from "../api/dashboard";
import { notificationText } from "../api/notifications";
import { listTasks, postponeTask } from "../api/tasks";
import type {
  CheckInPublic,
  DailyDashboard,
  MedicationEventStatus,
  TaskFailureReasonType,
  TaskPublic,
} from "../api/types";
import { DateTimeWidget } from "../components/DateTimeWidget";
import { MedicationDoseRow } from "../components/MedicationDoseRow";
import { StateBadge } from "../components/StateBadge";
import { TaskCard } from "../components/TaskCard";
import { compareActionable } from "../taskOrdering";
import { SuggestNow } from "../components/SuggestNow";
import { energyFromFunctioning } from "../taskTemplates";
import { TASK_FAILURE_REASON_LABELS, TASK_FAILURE_REASON_ORDER } from "../labels";

/**
 * Redesign da Home (2026-09) — reorganização de LAYOUT/UX, não
 * reescrita de lógica: todo dado e toda chamada de API já existiam
 * (dashboard diário, tarefas, check-in). Estrutura pedida:
 *
 *   Agora (estado + ação rápida)
 *   → Como você está funcionando (4 chips não-clínicos → sense_of_functioning)
 *   → Próxima missão (reaproveita TaskCard já existente)
 *   → Estou enrolando (reaproveita postponeTask, chips em vez de select)
 *   → stats do dia
 *   → Detalhes de hoje (medicação, intervenções, notificações — progressive disclosure)
 *
 * As únicas adições de API client são `updateCheckin` (PATCH) e
 * `listCheckins` (GET) — endpoints que já existiam no backend desde a
 * ETAPA 11, nunca expostos no frontend até agora. Nenhum arquivo de
 * backend foi tocado.
 */

const FUNCTIONING_OPTIONS: { value: number; label: string }[] = [
  { value: 1, label: "Travado" },
  { value: 2, label: "Devagar" },
  { value: 4, label: "Funcionando" },
  { value: 5, label: "No ritmo" },
];

function pickNextTask(tasks: TaskPublic[]): TaskPublic | null {
  const actionable = tasks.filter((t) => t.status !== "completed" && t.status !== "cancelled");
  if (actionable.length === 0) return null;
  return [...actionable].sort(compareActionable)[0];
}

export function DashboardPage() {
  const [data, setData] = useState<DailyDashboard | null>(null);
  const [tasks, setTasks] = useState<TaskPublic[] | null>(null);
  const [recentCheckins, setRecentCheckins] = useState<CheckInPublic[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [functioningSaving, setFunctioningSaving] = useState(false);
  const [functioningError, setFunctioningError] = useState<string | null>(null);
  const [procrastinatingError, setProcrastinatingError] = useState<string | null>(null);
  const [procrastinatingReason, setProcrastinatingReason] = useState<TaskFailureReasonType | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([getDailyDashboard(), listTasks(), listCheckins({ limit: 7 })])
      .then(([dashboard, taskList, checkins]) => {
        if (cancelled) return;
        setData(dashboard);
        setTasks(taskList);
        setRecentCheckins(checkins);
      })
      .catch((err) => {
        if (!cancelled) setError(describeError(err, "não foi possível carregar seu painel"));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <p className="page-loading">carregando…</p>;
  }
  if (error) {
    return (
      <p className="form-error" role="alert">
        {error}
      </p>
    );
  }
  if (!data) {
    return null;
  }

  function handleDoseConfirmed(scheduleId: string, status: MedicationEventStatus) {
    setData((prev) =>
      prev
        ? {
            ...prev,
            medications_today: prev.medications_today.map((dose) =>
              dose.schedule_id === scheduleId ? { ...dose, status } : dose,
            ),
          }
        : prev,
    );
  }

  async function handleFunctioningChip(value: number) {
    setFunctioningError(null);
    setFunctioningSaving(true);
    try {
      const updated = data?.checkin
        ? await updateCheckin(data.checkin.checkin_date, { sense_of_functioning: value })
        : await submitCheckin({ sense_of_functioning: value });
      setData((prev) => (prev ? { ...prev, checkin: updated, checkin_submitted_today: true } : prev));
    } catch (err) {
      setFunctioningError(describeError(err, "não foi possível salvar"));
    } finally {
      setFunctioningSaving(false);
    }
  }

  function handleTaskChanged(updated: TaskPublic) {
    setTasks((prev) => (prev ?? []).map((t) => (t.id === updated.id ? updated : t)));
  }

  function handleTaskCreated(task: TaskPublic) {
    setTasks((prev) => [task, ...(prev ?? [])]);
  }

  const nextTask = tasks ? pickNextTask(tasks) : null;

  async function handleProcrastinatingChip(reason: TaskFailureReasonType) {
    if (!nextTask) return;
    setProcrastinatingError(null);
    setProcrastinatingReason(reason);
    try {
      const updated = await postponeTask(nextTask.id, { reason, custom_text: null });
      handleTaskChanged(updated);
    } catch (err) {
      setProcrastinatingError(describeError(err, "não foi possível registrar"));
    } finally {
      setProcrastinatingReason(null);
    }
  }

  const checkinDaysThisWeek = recentCheckins?.length ?? 0;
  const pendingTasksCount = (tasks ?? []).filter((t) => t.status !== "completed" && t.status !== "cancelled").length;
  const completedTasksCount = (tasks ?? []).filter((t) => t.status === "completed").length;
  const detailsCount =
    data.medications_today.length + data.active_interventions.length + data.unread_notifications_count;

  return (
    <div className="home-page">
      {/* Agora */}
      <section className="home-section">
        <DateTimeWidget />
        <StateBadge state={data.state} reason={data.state_reason} />
      </section>

      {/* Como você está funcionando */}
      <section className="card home-section">
        <h2>Como você está funcionando</h2>
        <div className="chip-row" role="group" aria-label="Como você está funcionando">
          {FUNCTIONING_OPTIONS.map((option) => (
            <button
              type="button"
              key={option.value}
              className={`chip-option${data.checkin?.sense_of_functioning === option.value ? " chip-option--selected" : ""}`}
              onClick={() => void handleFunctioningChip(option.value)}
              disabled={functioningSaving}
              aria-pressed={data.checkin?.sense_of_functioning === option.value}
            >
              {option.label}
            </button>
          ))}
        </div>
        {functioningError && (
          <p className="form-error" role="alert">
            {functioningError}
          </p>
        )}
        {data.checkin_submitted_today ? (
          <p className="checkin-hint">Você já registrou seu check-in de hoje.</p>
        ) : (
          <p className="checkin-hint">
            Isso já conta como um começo de check-in — se quiser detalhar mais,{" "}
            <Link to="/checkin">complete o check-in</Link>.
          </p>
        )}
      </section>

      {/* Próxima missão */}
      <section className="home-section">
        <div className="home-section__head">
          <h2>Próxima missão</h2>
          <Link className="home-section__link" to="/tarefas">
            + adicionar sem escrever
          </Link>
        </div>
        {nextTask ? (
          <ul className="relationship-list">
            <TaskCard key={nextTask.id} task={nextTask} relationshipLabel={null} onChanged={handleTaskChanged} highlight />
          </ul>
        ) : (
          <SuggestNow
            tasks={tasks}
            energy={energyFromFunctioning(data.checkin?.sense_of_functioning)}
            onCreated={handleTaskCreated}
          />
        )}
      </section>

      {/* Estou enrolando */}
      {nextTask && (
        <section className="card home-section">
          <h2>Estou enrolando</h2>
          <p className="checkin-hint">Toque no motivo — adia a missão acima na hora, sem formulário.</p>
          <div className="chip-row" role="group" aria-label="Por que está enrolando">
            {TASK_FAILURE_REASON_ORDER.map((reason) => (
              <button
                type="button"
                key={reason}
                className="chip-option"
                onClick={() => void handleProcrastinatingChip(reason)}
                disabled={procrastinatingReason !== null}
              >
                {procrastinatingReason === reason ? "Adiando…" : TASK_FAILURE_REASON_LABELS[reason]}
              </button>
            ))}
          </div>
          {procrastinatingError && (
            <p className="form-error" role="alert">
              {procrastinatingError}
            </p>
          )}
        </section>
      )}

      {/* stats do dia */}
      <section className="card home-section home-stats">
        <p>Check-in feito {checkinDaysThisWeek} de 7 dias esta semana.</p>
        <p>
          {pendingTasksCount} {pendingTasksCount === 1 ? "missão pendente" : "missões pendentes"}
          {" · "}
          {completedTasksCount} concluída{completedTasksCount === 1 ? "" : "s"}
        </p>
      </section>

      {/* Detalhes de hoje */}
      <details className="home-more">
        <summary>Detalhes de hoje{detailsCount > 0 ? ` (${detailsCount})` : ""}</summary>
        <div className="home-more__content">
          {data.medications_today.length > 0 && (
            <section className="card">
              <h2>Medicação de hoje</h2>
              <ul className="plain-list">
                {data.medications_today.map((dose) => (
                  <MedicationDoseRow key={dose.schedule_id} dose={dose} onConfirmed={handleDoseConfirmed} />
                ))}
              </ul>
            </section>
          )}

          {data.active_interventions.length > 0 && (
            <section className="card">
              <h2>Em andamento</h2>
              <ul className="plain-list">
                {data.active_interventions.map((item) => (
                  <li key={item.id}>{item.suggestion_text}</li>
                ))}
              </ul>
            </section>
          )}

          {data.unread_notifications_count > 0 && (
            <section className="card">
              <h2>Notificações</h2>
              <p>
                Você tem {data.unread_notifications_count} não lida{data.unread_notifications_count === 1 ? "" : "s"}.
              </p>
              <ul className="plain-list">
                {data.recent_notifications
                  .filter((item) => !item.read_at)
                  .slice(0, 3)
                  .map((item) => (
                    <li key={item.id}>{notificationText(item)}</li>
                  ))}
              </ul>
              <Link className="button button--ghost" to="/notificacoes">
                Ver notificações
              </Link>
            </section>
          )}

          {detailsCount === 0 && <p className="checkin-hint">nada pendente por aqui.</p>}
        </div>
      </details>
    </div>
  );
}
