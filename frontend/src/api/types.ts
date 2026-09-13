/**
 * ETAPA 27 — tipos TS espelhando os schemas Pydantic do backend, só
 * para os endpoints que o frontend já consome nesta primeira leva
 * (auth, dashboard diário, check-in). Escrito à mão, não gerado a
 * partir do OpenAPI — decisão de escopo: um gerador de tipos
 * (openapi-typescript e afins) é uma dependência a mais que só se
 * paga quando a superfície da API consumida crescer o bastante pra
 * a cópia manual doer; hoje não dói.
 */

export interface UserPublic {
  id: string;
  email: string;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type AlertState = "green" | "yellow" | "red";

export interface CheckInPublic {
  id: string;
  checkin_date: string;
  mood: number | null;
  energy: number | null;
  anxiety: number | null;
  ability_to_start_tasks: number | null;
  willingness_to_interact: number | null;
  sleep_quality: number | null;
  sense_of_functioning: number | null;
  extra_answers: Record<string, unknown> | null;
  submitted_at: string;
  created_at: string;
  updated_at: string;
}

export interface CheckInCreate {
  checkin_date?: string | null;
  mood?: number | null;
  energy?: number | null;
  anxiety?: number | null;
  ability_to_start_tasks?: number | null;
  willingness_to_interact?: number | null;
  sleep_quality?: number | null;
  sense_of_functioning?: number | null;
  extra_answers?: Record<string, unknown> | null;
}

export type MedicationEventStatus =
  | "taken"
  | "not_taken"
  | "forgot_to_confirm"
  | "skipped_deliberately"
  | "unavailable";

export interface MedicationDoseToday {
  medication_id: string;
  medication_name: string;
  schedule_id: string;
  time_of_day: string;
  status: MedicationEventStatus | null;
}

export type MedicationSkipReason =
  | "esqueci"
  | "rotina_mudou"
  | "nao_consegui_levantar"
  | "efeito_adverso"
  | "medo"
  | "medicamento_indisponivel"
  | "decisao_propria"
  | "outro";

export interface MedicationPublic {
  id: string;
  name: string;
  dosage_note: string | null;
  notes: string | null;
  reminder_enabled: boolean;
  reminder_repeat_enabled: boolean;
  discontinued_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MedicationCreate {
  name: string;
  dosage_note?: string | null;
  notes?: string | null;
  reminder_enabled?: boolean;
  reminder_repeat_enabled?: boolean;
}

export interface SchedulePublic {
  id: string;
  medication_id: string;
  time_of_day: string;
  weekdays: number[] | null;
}

export interface ScheduleCreate {
  time_of_day: string;
  weekdays?: number[] | null;
}

export interface MedicationEventCreate {
  scheduled_for: string;
  status: MedicationEventStatus;
  skip_reason?: MedicationSkipReason | null;
  custom_reason_text?: string | null;
}

export interface MedicationEventPublic {
  id: string;
  schedule_id: string;
  scheduled_for: string;
  status: MedicationEventStatus;
  skip_reason: MedicationSkipReason | null;
  custom_reason_text: string | null;
  confirmed_at: string | null;
}

/**
 * ETAPA 27 (3ª leva) — rotina de referência + eventos de vida.
 * Espelha `app/schemas/routine.py`.
 */
export type ActivationDomain =
  | "levantar"
  | "higiene"
  | "alimentacao"
  | "sair_de_casa"
  | "caminhar"
  | "atividade_fisica"
  | "lazer"
  | "interacao_social"
  | "trabalho"
  | "estudo"
  | "atividade_significativa"
  | "tarefas_basicas";

export type LifeEventType = "travel" | "vacation" | "new_job" | "illness" | "move" | "other";

export interface RoutineFields {
  typical_wake_time?: string | null;
  typical_sleep_time?: string | null;
  goes_out_on_weekdays?: boolean | null;
  social_contact_days_per_week?: number | null;
  typical_tasks_postponed_on_good_day?: number | null;
  selected_activation_domains?: ActivationDomain[] | null;
  notes?: string | null;
}

export interface RoutineCreate extends RoutineFields {
  period_start?: string | null;
}

export type RoutineUpdate = RoutineFields;

export interface RoutinePublic {
  id: string;
  version: number;
  period_start: string;
  period_end: string | null;
  typical_wake_time: string | null;
  typical_sleep_time: string | null;
  goes_out_on_weekdays: boolean | null;
  social_contact_days_per_week: number | null;
  typical_tasks_postponed_on_good_day: number | null;
  selected_activation_domains: string[] | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface LifeEventCreate {
  event_type: LifeEventType;
  description?: string | null;
  start_date: string;
  end_date?: string | null;
}

export interface LifeEventPublic {
  id: string;
  event_type: LifeEventType;
  description: string | null;
  start_date: string;
  end_date: string | null;
  created_at: string;
}

/**
 * ETAPA 27 (4ª leva) — alertas, motor de desvio, explicabilidade e
 * painel analítico. A maioria dos textos (label, explanation,
 * reason_summary) já vem pronta em PT-BR do backend — o frontend só
 * organiza, nunca traduz ou recalcula (mesmo princípio do
 * `explainability_service`).
 */
export type DeviationEngine = "executive" | "avoidance" | "activation" | "stability";

export interface AlertPublic {
  id: string;
  state: AlertState;
  triggering_deviation_id: string | null;
  reason_summary: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  created_at: string;
}

export interface DeviationEventPublic {
  id: string;
  engine: DeviationEngine;
  detected_at: string;
  magnitude: number;
  duration_days: number;
  domains_count: number;
  convergence_score: number | null;
  triggering_indicator_keys: string[];
  baseline_snapshot: Record<string, unknown>;
  explanation: string;
}

export interface IndicatorExplanation {
  indicator_key: string;
  label: string;
  baseline_mean: number | null;
  recent_value: number | null;
  streak_days: number | null;
  direction: string | null;
}

export interface EngineExplanation {
  engine: DeviationEngine;
  engine_label: string;
  detected_at: string;
  duration_days: number;
  convergence_score: number | null;
  explanation: string;
  indicators: IndicatorExplanation[];
}

export interface AlertExplanation {
  alert_id: string;
  state: AlertState;
  reason_summary: string;
  engines_count: number;
  total_engines: number;
  breadth_score: number | null;
  engines: EngineExplanation[];
}

export interface AlertTimelineEntry {
  id: string;
  state: AlertState;
  reason_summary: string;
  created_at: string;
  resolved_at: string | null;
}

export interface IndicatorTrend {
  indicator_key: IndicatorKey;
  label: string;
  baseline_mean: number | null;
  recent_value: number | null;
  trend_slope: number | null;
  sample_size: number | null;
}

export interface DeviationTimelineEntry {
  id: string;
  engine: DeviationEngine;
  engine_label: string;
  detected_at: string;
  magnitude: number;
  duration_days: number;
}

export interface MedicationAdherenceSummary {
  period_days: number;
  scheduled_count: number;
  taken_count: number;
  adherence_rate: number | null;
}

export interface InterventionStatsSummary {
  total: number;
  by_status: Record<string, number>;
  helped_count: number;
  not_helped_count: number;
  no_result_count: number;
}

export interface AnalyticsDashboard {
  period_days: number;
  alert_timeline: AlertTimelineEntry[];
  indicators: IndicatorTrend[];
  deviation_timeline: DeviationTimelineEntry[];
  medication_adherence: MedicationAdherenceSummary;
  intervention_stats: InterventionStatsSummary;
}

export interface InterventionPublic {
  id: string;
  type: string;
  status: string;
  related_task_id: string | null;
  related_deviation_id: string | null;
  support_relationship_id: string | null;
  suggestion_text: string;
  created_at: string;
  updated_at: string;
}

export interface NotificationPublic {
  id: string;
  type: string;
  channel: string;
  priority: string;
  payload: Record<string, unknown>;
  grouped_with: string | null;
  scheduled_for: string | null;
  sent_at: string | null;
  read_at: string | null;
  created_at: string;
}

export interface DailyDashboard {
  state: AlertState;
  state_reason: string;
  state_since: string | null;
  checkin_submitted_today: boolean;
  checkin: CheckInPublic | null;
  medications_today: MedicationDoseToday[];
  active_interventions: InterventionPublic[];
  unread_notifications_count: number;
  recent_notifications: NotificationPublic[];
}

/**
 * ETAPA 27 (2ª leva) — rede de confiança: convite, permissões
 * granulares e observações externas. Espelha `app/schemas/trust.py` e
 * `PermissionKey`/`IndicatorKey`/`Observation*` de `app/models/enums.py`.
 */
export type PermissionKey =
  | "record_observation"
  | "suggest_task"
  | "create_task"
  | "help_with_task"
  | "confirm_event"
  | "request_checkin"
  | "receive_alert_yellow"
  | "receive_alert_red"
  | "view_routine"
  | "view_medication"
  | "view_specific_indicators"
  | "view_full_history"
  | "access_crisis_plan";

export type RelationshipStatus = "pending" | "accepted" | "revoked";

export type IndicatorKey =
  | "sleep_hours"
  | "wake_time_minutes"
  | "sleep_time_minutes"
  | "mood"
  | "energy"
  | "anxiety"
  | "ability_to_start_tasks"
  | "tasks_started_count"
  | "tasks_postponed_count"
  | "tasks_completed_count"
  | "left_home"
  | "social_contact"
  | "activity_level"
  | "avoidance_load"
  | "medication_adherence";

export type ObservationCategory =
  | "isolamento"
  | "ausencia_trabalho"
  | "ausencia_estudos"
  | "mudanca_sono"
  | "autocuidado_reduzido"
  | "comunicacao_reduzida"
  | "mudanca_incomum"
  | "irritabilidade"
  | "dificuldade_funcionar"
  | "ausencia"
  | "outro";

export type ObservationSince = "hoje" | "2_3_dias" | "mais_de_3_dias";

export type ObservationIntensity = "leve" | "relevante" | "seria";

export interface PermissionPublic {
  permission_key: PermissionKey;
  is_granted: boolean;
  indicator_scope: IndicatorKey[] | null;
  granted_at: string | null;
  revoked_at: string | null;
}

export interface RelationshipPublic {
  id: string;
  invite_email: string;
  relationship_label: string | null;
  status: RelationshipStatus;
  invited_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  permissions: PermissionPublic[];
}

export interface PermissionUpdate {
  permission_key: PermissionKey;
  is_granted: boolean;
  indicator_scope: IndicatorKey[] | null;
}

export interface ObservationPublic {
  id: string;
  relationship_id: string;
  category: ObservationCategory;
  since: ObservationSince;
  intensity: ObservationIntensity;
  note: string | null;
  recorded_at: string;
}

export interface ObservationCreate {
  category: ObservationCategory;
  since: ObservationSince;
  intensity: ObservationIntensity;
  note?: string | null;
}

// --- ETAPA 27 (6ª leva): painel operacional da pessoa de confiança ---

/** Espelha `RelationshipAsTrustedPublic` de `app/schemas/trust.py`. */
export interface RelationshipAsTrustedPublic extends RelationshipPublic {
  owner_display_name: string;
}

/** Espelha `TrustedDashboard` de `app/schemas/dashboard.py` — cada
 * seção vem `null` quando a permissão correspondente não foi
 * concedida, nunca uma lista vazia fingindo "sem dado". */
export interface TrustedDashboard {
  relationship_id: string;
  state: AlertState | null;
  state_reason: string | null;
  medication_adherence: MedicationAdherenceSummary | null;
  indicators: IndicatorTrend[] | null;
  alert_timeline: AlertTimelineEntry[] | null;
  deviation_timeline: DeviationTimelineEntry[] | null;
  pending_support_requests: InterventionPublic[] | null;
}

// --- ETAPA 27 (5ª leva): plano pessoal e configurações de conta ---

export type PersonalPlanSignal =
  | "faltas"
  | "isolamento"
  | "sono"
  | "medicacao"
  | "abandono_de_tarefas"
  | "uso_de_substancias"
  | "comunicacao"
  | "autocuidado";

export interface PersonalPlanRulePublic {
  id: string;
  signal_key: PersonalPlanSignal;
  threshold_description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PersonalPlanPublic {
  id: string;
  title: string;
  description: string;
  is_active: boolean;
  rules: PersonalPlanRulePublic[];
  created_at: string;
  updated_at: string;
}

export interface PersonalPlanCreate {
  title: string;
  description: string;
}

export interface PersonalPlanUpdate {
  title?: string;
  description?: string;
}

export interface PersonalPlanRuleCreate {
  signal_key: PersonalPlanSignal;
  threshold_description: string;
}

export interface PersonalPlanRuleUpdate {
  threshold_description?: string;
  is_active?: boolean;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface AccountDeactivateRequest {
  password: string;
}

export interface AccountDeactivateResponse {
  deactivated: boolean;
  deactivated_at: string;
}

// --- ETAPA 27 (7ª leva): visualizador de auditoria ---

export type AuditAction =
  | "login"
  | "password_change"
  | "invite_sent"
  | "permission_granted"
  | "permission_revoked"
  | "external_observation_recorded"
  | "restricted_data_access_denied"
  | "plan_changed"
  | "critical_alert"
  | "data_exported"
  | "account_deletion_requested";

/** Espelha `AuditLogEntry` de `app/schemas/audit.py`. `metadata` nunca
 * contém dado sensível (já garantido por quem grava cada `AuditLog`
 * no backend); `actor_is_self=false` cobre "uma pessoa de confiança
 * ou o sistema fez algo relacionado à sua conta" sem revelar qual
 * pessoa de confiança especificamente — decisão de privacidade do
 * backend (ETAPA 26), não algo pra "consertar" na UI. */
export interface AuditLogEntry {
  id: string;
  action: AuditAction;
  actor_is_self: boolean;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

// --- ETAPA 27 (8ª leva): tarefas (ETAPA 10) + sugerir tarefa pela pessoa de confiança ---

export type TaskStatus = "pending" | "started" | "paused" | "postponed" | "completed" | "cancelled";

export type TaskPriority = "low" | "medium" | "high";

export type TaskOrigin = "self" | "trusted_person_suggestion";

export type TaskFailureReasonType =
  | "esqueci"
  | "nao_consegui_comecar"
  | "fiquei_ansioso"
  | "nao_tive_energia"
  | "nao_queria_enfrentar"
  | "me_distrai"
  | "nao_tive_tempo"
  | "tarefa_grande_demais"
  | "prioridade_mudou"
  | "outro";

export interface TaskPublic {
  id: string;
  title: string;
  description: string | null;
  category: string | null;
  priority: TaskPriority;
  status: TaskStatus;
  due_date: string | null;
  estimated_minutes: number | null;
  actual_minutes: number | null;
  started_at: string | null;
  completed_at: string | null;
  postponed_count: number;
  attempt_count: number;
  origin: TaskOrigin;
  source_relationship_id: string | null;
  support_relationship_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskCreate {
  title: string;
  description?: string | null;
  category?: string | null;
  priority?: TaskPriority;
  due_date?: string | null;
  estimated_minutes?: number | null;
}

export interface TaskFailureReasonInput {
  reason: TaskFailureReasonType;
  custom_text?: string | null;
}

/** Espelha `SuggestTaskRequest` — usado pela PESSOA DE CONFIANÇA, nunca pelo dono. */
export interface SuggestTaskRequest {
  title: string;
  description?: string | null;
  due_date?: string | null;
}
