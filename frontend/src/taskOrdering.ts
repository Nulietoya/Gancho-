import type { TaskPriority, TaskPublic } from "./api/types";

const STATUS_WEIGHT: Record<string, number> = { started: 0, paused: 1, pending: 2, postponed: 3 };
const PRIORITY_WEIGHT: Record<TaskPriority, number> = { high: 0, medium: 1, low: 2 };

function isToday(iso: string | null): boolean {
  if (!iso) return false;
  const d = new Date(iso);
  const now = new Date();
  return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
}

/** Ordena a fila do mesmo jeito que a Home escolhe a "Próxima missão". */
export function compareActionable(a: TaskPublic, b: TaskPublic): number {
  const byStatus = (STATUS_WEIGHT[a.status] ?? 9) - (STATUS_WEIGHT[b.status] ?? 9);
  if (byStatus !== 0) return byStatus;
  const byPriority = PRIORITY_WEIGHT[a.priority] - PRIORITY_WEIGHT[b.priority];
  if (byPriority !== 0) return byPriority;
  if (a.due_date && b.due_date) return a.due_date.localeCompare(b.due_date);
  if (a.due_date) return -1;
  if (b.due_date) return 1;
  return a.created_at.localeCompare(b.created_at);
}

export function groupTasks(tasks: TaskPublic[]) {
  const now: TaskPublic[] = [];
  const queue: TaskPublic[] = [];
  const doneToday: TaskPublic[] = [];
  const archive: TaskPublic[] = [];
  for (const t of tasks) {
    if (t.status === "started" || t.status === "paused") now.push(t);
    else if (t.status === "pending" || t.status === "postponed") queue.push(t);
    else if (t.status === "completed" && isToday(t.completed_at)) doneToday.push(t);
    else archive.push(t);
  }
  now.sort(compareActionable);
  queue.sort(compareActionable);
  return { now, queue, doneToday, archive };
}
