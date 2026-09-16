import { ApiError } from "./client";
import { apiJson } from "./apiFetch";
import type {
  InterventionPublic,
  InviteCreatedResponse,
  ObservationCreate,
  ObservationPublic,
  OwnerRelationshipPublic,
  PermissionUpdate,
  PersonalPlanPublic,
  RelationshipAsTrustedPublic,
  RelationshipPublic,
  SuggestTaskRequest,
  TaskPublic,
  TrustedDashboard,
} from "./types";

export function listTrustedPeople(): Promise<OwnerRelationshipPublic[]> {
  return apiJson<OwnerRelationshipPublic[]>("/trusted-people");
}

export function inviteTrustedPerson(email: string, relationshipLabel: string | null): Promise<InviteCreatedResponse> {
  return apiJson<InviteCreatedResponse>("/trusted-people/invite", {
    method: "POST",
    body: JSON.stringify({ email, relationship_label: relationshipLabel }),
  });
}

export function acceptInvite(inviteToken: string): Promise<RelationshipPublic> {
  return apiJson<RelationshipPublic>("/trusted-people/accept", {
    method: "POST",
    body: JSON.stringify({ invite_token: inviteToken }),
  });
}

export function updatePermissions(
  relationshipId: string,
  permissions: PermissionUpdate[],
): Promise<RelationshipPublic> {
  return apiJson<RelationshipPublic>(`/trusted-people/${relationshipId}/permissions`, {
    method: "PUT",
    body: JSON.stringify({ permissions }),
  });
}

export function revokeRelationship(relationshipId: string): Promise<RelationshipPublic> {
  return apiJson<RelationshipPublic>(`/trusted-people/${relationshipId}/revoke`, {
    method: "POST",
  });
}

export function listObservations(relationshipId: string): Promise<ObservationPublic[]> {
  return apiJson<ObservationPublic[]>(`/trusted-people/${relationshipId}/observations`);
}

// --- ETAPA 27 (6ª leva): painel operacional da pessoa de confiança ---

/** Contas que EU acompanho como pessoa de confiança — visão inversa de `listTrustedPeople`. */
export function listWatchedAccounts(): Promise<RelationshipAsTrustedPublic[]> {
  return apiJson<RelationshipAsTrustedPublic[]>("/trusted-people/watching");
}

export function getTrustedDashboard(relationshipId: string): Promise<TrustedDashboard> {
  return apiJson<TrustedDashboard>(`/trusted-people/${relationshipId}/dashboard`);
}

/** 404 quando o dono ainda não escreveu um plano, ou quando `ACCESS_CRISIS_PLAN` não foi concedida a esta relação. */
export async function getTrustedPersonalPlan(relationshipId: string): Promise<PersonalPlanPublic | null> {
  try {
    return await apiJson<PersonalPlanPublic>(`/trusted-people/${relationshipId}/personal-plan`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return null;
    }
    throw err;
  }
}

export function recordObservationAsTrusted(
  relationshipId: string,
  data: ObservationCreate,
): Promise<ObservationPublic> {
  return apiJson<ObservationPublic>(`/trusted-people/${relationshipId}/observations`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function acceptInterventionAsTrusted(
  relationshipId: string,
  interventionId: string,
): Promise<InterventionPublic> {
  return apiJson<InterventionPublic>(`/trusted-people/${relationshipId}/interventions/${interventionId}/accept`, {
    method: "POST",
  });
}

// --- ETAPA 27 (8ª leva): sugerir tarefa pela pessoa de confiança ---

/** A tarefa nasce na conta do DONO (`relationship.owner_user_id`), nunca na de quem sugere. */
export function suggestTaskAsTrusted(relationshipId: string, data: SuggestTaskRequest): Promise<TaskPublic> {
  return apiJson<TaskPublic>(`/trusted-people/${relationshipId}/tasks/suggest`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}
