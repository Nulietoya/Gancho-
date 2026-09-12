import { apiJson } from "./apiFetch";
import { ApiError } from "./client";
import type {
  PersonalPlanCreate,
  PersonalPlanPublic,
  PersonalPlanRuleCreate,
  PersonalPlanRulePublic,
  PersonalPlanRuleUpdate,
  PersonalPlanUpdate,
} from "./types";

/** `GET /personal-plan` devolve 404 quando não há plano ativo — mesmo padrão de `getCurrentRoutine`. */
export async function getPersonalPlan(): Promise<PersonalPlanPublic | null> {
  try {
    return await apiJson<PersonalPlanPublic>("/personal-plan");
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return null;
    }
    throw err;
  }
}

export function createPersonalPlan(data: PersonalPlanCreate): Promise<PersonalPlanPublic> {
  return apiJson<PersonalPlanPublic>("/personal-plan", { method: "POST", body: JSON.stringify(data) });
}

export function updatePersonalPlan(data: PersonalPlanUpdate): Promise<PersonalPlanPublic> {
  return apiJson<PersonalPlanPublic>("/personal-plan", { method: "PATCH", body: JSON.stringify(data) });
}

/** Sem endpoint de reativação, de propósito (ver docs/decisions.md, ETAPA 25) — depois disso a próxima leitura volta a 404. */
export function deactivatePersonalPlan(): Promise<PersonalPlanPublic> {
  return apiJson<PersonalPlanPublic>("/personal-plan/deactivate", { method: "POST" });
}

export function addPersonalPlanRule(data: PersonalPlanRuleCreate): Promise<PersonalPlanRulePublic> {
  return apiJson<PersonalPlanRulePublic>("/personal-plan/rules", { method: "POST", body: JSON.stringify(data) });
}

export function updatePersonalPlanRule(
  ruleId: string,
  data: PersonalPlanRuleUpdate,
): Promise<PersonalPlanRulePublic> {
  return apiJson<PersonalPlanRulePublic>(`/personal-plan/rules/${ruleId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}
