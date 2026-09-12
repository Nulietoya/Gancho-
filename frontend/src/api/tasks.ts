import { apiJson } from "./apiFetch";
import type { TaskCreate, TaskFailureReasonInput, TaskPublic, TaskStatus } from "./types";

export function createTask(data: TaskCreate): Promise<TaskPublic> {
  return apiJson<TaskPublic>("/tasks", { method: "POST", body: JSON.stringify(data) });
}

export function listTasks(statusFilter?: TaskStatus): Promise<TaskPublic[]> {
  const query = statusFilter ? `?status_filter=${statusFilter}` : "";
  return apiJson<TaskPublic[]>(`/tasks${query}`);
}

export function startTask(taskId: string): Promise<TaskPublic> {
  return apiJson<TaskPublic>(`/tasks/${taskId}/start`, { method: "POST" });
}

export function resumeTask(taskId: string): Promise<TaskPublic> {
  return apiJson<TaskPublic>(`/tasks/${taskId}/resume`, { method: "POST" });
}

export function pauseTask(taskId: string): Promise<TaskPublic> {
  return apiJson<TaskPublic>(`/tasks/${taskId}/pause`, { method: "POST" });
}

/** Adiar sempre pede motivo (item 8) — nunca fica implícito no silêncio. */
export function postponeTask(taskId: string, data: TaskFailureReasonInput): Promise<TaskPublic> {
  return apiJson<TaskPublic>(`/tasks/${taskId}/postpone`, { method: "POST", body: JSON.stringify(data) });
}

export function completeTask(taskId: string): Promise<TaskPublic> {
  return apiJson<TaskPublic>(`/tasks/${taskId}/complete`, { method: "POST" });
}

/** Motivo é opcional ao cancelar — a tarefa pode ter deixado de fazer sentido, não ter sido evitada. */
export function cancelTask(taskId: string, data?: TaskFailureReasonInput): Promise<TaskPublic> {
  return apiJson<TaskPublic>(`/tasks/${taskId}/cancel`, {
    method: "POST",
    body: data ? JSON.stringify(data) : undefined,
  });
}
