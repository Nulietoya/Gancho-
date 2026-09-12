import { apiJson } from "./apiFetch";
import { ApiError } from "./client";
import type { LifeEventCreate, LifeEventPublic, RoutineCreate, RoutinePublic, RoutineUpdate } from "./types";

export async function getCurrentRoutine(): Promise<RoutinePublic | null> {
  try {
    return await apiJson<RoutinePublic>("/routines/current");
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return null;
    }
    throw err;
  }
}

export function createRoutine(data: RoutineCreate): Promise<RoutinePublic> {
  return apiJson<RoutinePublic>("/routines", { method: "POST", body: JSON.stringify(data) });
}

export function updateRoutine(data: RoutineUpdate): Promise<RoutinePublic> {
  return apiJson<RoutinePublic>("/routines/current", { method: "PATCH", body: JSON.stringify(data) });
}

export function startNewRoutineVersion(data: RoutineCreate): Promise<RoutinePublic> {
  return apiJson<RoutinePublic>("/routines/new-version", { method: "POST", body: JSON.stringify(data) });
}

export function listLifeEvents(): Promise<LifeEventPublic[]> {
  return apiJson<LifeEventPublic[]>("/life-events");
}

export function createLifeEvent(data: LifeEventCreate): Promise<LifeEventPublic> {
  return apiJson<LifeEventPublic>("/life-events", { method: "POST", body: JSON.stringify(data) });
}
