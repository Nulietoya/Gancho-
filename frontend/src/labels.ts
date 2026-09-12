/**
 * Rótulos em PT-BR pra enums do backend que aparecem em mais de uma
 * tela. Centralizado aqui em vez de duplicado em cada página — mesmo
 * raciocínio de "consolidar repetição" já aplicado no backend nas
 * revisões gerais.
 */
import type {
  ActivationDomain,
  AuditAction,
  IndicatorKey,
  LifeEventType,
  MedicationEventStatus,
  MedicationSkipReason,
  ObservationCategory,
  ObservationIntensity,
  ObservationSince,
  PermissionKey,
  PersonalPlanSignal,
  RelationshipStatus,
  TaskFailureReasonType,
  TaskPriority,
  TaskStatus,
} from "./api/types";

export const PERMISSION_LABELS: Record<PermissionKey, string> = {
  record_observation: "Registrar observações sobre você",
  suggest_task: "Sugerir uma tarefa ou ação",
  create_task: "Criar tarefas por você",
  help_with_task: "Aceitar pedidos de acompanhamento (body doubling)",
  confirm_event: "Confirmar eventos importantes da sua rotina",
  request_checkin: "Pedir que você faça um check-in",
  receive_alert_yellow: "Receber alerta de mudança sustentada (amarelo)",
  receive_alert_red: "Receber alerta de mudança em várias áreas (vermelho)",
  view_routine: "Ver sua rotina de referência",
  view_medication: "Ver sua adesão à medicação (taxa, nunca dose a dose)",
  view_specific_indicators: "Ver indicadores específicos que você escolher",
  view_full_history: "Ver seu histórico completo de estado",
  access_crisis_plan: "Acessar seu plano para quando você não perceber",
};

export const PERMISSION_ORDER: PermissionKey[] = [
  "receive_alert_yellow",
  "receive_alert_red",
  "record_observation",
  "suggest_task",
  "create_task",
  "help_with_task",
  "request_checkin",
  "confirm_event",
  "view_routine",
  "view_medication",
  "view_specific_indicators",
  "view_full_history",
  "access_crisis_plan",
];

export const INDICATOR_LABELS: Record<IndicatorKey, string> = {
  sleep_hours: "Horas de sono",
  wake_time_minutes: "Horário de acordar",
  sleep_time_minutes: "Horário de dormir",
  mood: "Humor",
  energy: "Energia",
  anxiety: "Ansiedade",
  ability_to_start_tasks: "Facilidade de começar tarefas",
  tasks_started_count: "Tarefas iniciadas",
  tasks_postponed_count: "Tarefas adiadas",
  tasks_completed_count: "Tarefas concluídas",
  left_home: "Saiu de casa",
  social_contact: "Contato social",
  activity_level: "Nível de atividade",
  avoidance_load: "Carga de evitação",
  medication_adherence: "Adesão à medicação",
};

export const INDICATOR_ORDER: IndicatorKey[] = [
  "mood",
  "energy",
  "anxiety",
  "ability_to_start_tasks",
  "sleep_hours",
  "wake_time_minutes",
  "sleep_time_minutes",
  "left_home",
  "social_contact",
  "activity_level",
  "avoidance_load",
  "tasks_started_count",
  "tasks_postponed_count",
  "tasks_completed_count",
  "medication_adherence",
];

export const RELATIONSHIP_STATUS_LABELS: Record<RelationshipStatus, string> = {
  pending: "Convite pendente",
  accepted: "Ativo",
  revoked: "Revogado",
};

export const OBSERVATION_CATEGORY_LABELS: Record<ObservationCategory, string> = {
  isolamento: "Isolamento",
  ausencia_trabalho: "Ausência no trabalho",
  ausencia_estudos: "Ausência nos estudos",
  mudanca_sono: "Mudança no sono",
  autocuidado_reduzido: "Autocuidado reduzido",
  comunicacao_reduzida: "Comunicação reduzida",
  mudanca_incomum: "Mudança incomum de comportamento",
  irritabilidade: "Irritabilidade",
  dificuldade_funcionar: "Dificuldade de funcionar no dia a dia",
  ausencia: "Ausência",
  outro: "Outro",
};

export const OBSERVATION_CATEGORY_ORDER: ObservationCategory[] = [
  "isolamento",
  "ausencia_trabalho",
  "ausencia_estudos",
  "mudanca_sono",
  "autocuidado_reduzido",
  "comunicacao_reduzida",
  "irritabilidade",
  "dificuldade_funcionar",
  "mudanca_incomum",
  "ausencia",
  "outro",
];

export const OBSERVATION_SINCE_LABELS: Record<ObservationSince, string> = {
  hoje: "desde hoje",
  "2_3_dias": "há 2-3 dias",
  mais_de_3_dias: "há mais de 3 dias",
};

export const OBSERVATION_SINCE_ORDER: ObservationSince[] = ["hoje", "2_3_dias", "mais_de_3_dias"];

export const OBSERVATION_INTENSITY_LABELS: Record<ObservationIntensity, string> = {
  leve: "leve",
  relevante: "relevante",
  seria: "séria",
};

export const OBSERVATION_INTENSITY_ORDER: ObservationIntensity[] = ["leve", "relevante", "seria"];

export const MEDICATION_STATUS_LABELS: Record<MedicationEventStatus, string> = {
  taken: "tomado",
  not_taken: "não tomado",
  forgot_to_confirm: "esquecido de confirmar",
  skipped_deliberately: "pulado deliberadamente",
  unavailable: "indisponível",
};

export const MEDICATION_SKIP_REASON_LABELS: Record<MedicationSkipReason, string> = {
  esqueci: "esqueci",
  rotina_mudou: "a rotina mudou",
  nao_consegui_levantar: "não consegui levantar",
  efeito_adverso: "efeito adverso",
  medo: "medo",
  medicamento_indisponivel: "medicamento indisponível",
  decisao_propria: "decisão própria",
  outro: "outro",
};

export const ACTIVATION_DOMAIN_LABELS: Record<ActivationDomain, string> = {
  levantar: "Levantar da cama",
  higiene: "Higiene pessoal",
  alimentacao: "Alimentação",
  sair_de_casa: "Sair de casa",
  caminhar: "Caminhar",
  atividade_fisica: "Atividade física",
  lazer: "Lazer",
  interacao_social: "Interação social",
  trabalho: "Trabalho",
  estudo: "Estudo",
  atividade_significativa: "Atividade significativa",
  tarefas_basicas: "Tarefas básicas do dia a dia",
};

export const ACTIVATION_DOMAIN_ORDER: ActivationDomain[] = [
  "levantar",
  "higiene",
  "alimentacao",
  "sair_de_casa",
  "caminhar",
  "atividade_fisica",
  "lazer",
  "interacao_social",
  "trabalho",
  "estudo",
  "atividade_significativa",
  "tarefas_basicas",
];

export const PERSONAL_PLAN_SIGNAL_LABELS: Record<PersonalPlanSignal, string> = {
  faltas: "Faltas (trabalho, estudos, compromissos)",
  isolamento: "Isolamento",
  sono: "Mudança no sono",
  medicacao: "Adesão à medicação",
  abandono_de_tarefas: "Abandono de tarefas",
  uso_de_substancias: "Uso de substâncias",
  comunicacao: "Comunicação com outras pessoas",
  autocuidado: "Autocuidado",
};

export const PERSONAL_PLAN_SIGNAL_ORDER: PersonalPlanSignal[] = [
  "sono",
  "isolamento",
  "faltas",
  "abandono_de_tarefas",
  "medicacao",
  "comunicacao",
  "autocuidado",
  "uso_de_substancias",
];

export const LIFE_EVENT_TYPE_LABELS: Record<LifeEventType, string> = {
  travel: "Viagem",
  vacation: "Férias",
  new_job: "Novo emprego",
  illness: "Doença",
  move: "Mudança de casa/cidade",
  other: "Outro",
};

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  pending: "Pendente",
  started: "Em andamento",
  paused: "Pausada",
  postponed: "Adiada",
  completed: "Concluída",
  cancelled: "Cancelada",
};

/** Reaproveita as 3 variantes de `.status-badge` já existentes — sem CSS novo. */
export const TASK_STATUS_BADGE_VARIANT: Record<TaskStatus, "accepted" | "pending" | "revoked"> = {
  pending: "pending",
  started: "accepted",
  paused: "pending",
  postponed: "pending",
  completed: "accepted",
  cancelled: "revoked",
};

export const TASK_PRIORITY_LABELS: Record<TaskPriority, string> = {
  low: "Baixa",
  medium: "Média",
  high: "Alta",
};

export const TASK_PRIORITY_ORDER: TaskPriority[] = ["low", "medium", "high"];

export const TASK_FAILURE_REASON_LABELS: Record<TaskFailureReasonType, string> = {
  esqueci: "Esqueci",
  nao_consegui_comecar: "Não consegui começar",
  fiquei_ansioso: "Fiquei ansioso(a)",
  nao_tive_energia: "Não tive energia",
  nao_queria_enfrentar: "Não queria enfrentar",
  me_distrai: "Me distraí",
  nao_tive_tempo: "Não tive tempo",
  tarefa_grande_demais: "Tarefa grande demais",
  prioridade_mudou: "Prioridade mudou",
  outro: "Outro",
};

export const TASK_FAILURE_REASON_ORDER: TaskFailureReasonType[] = [
  "esqueci",
  "nao_consegui_comecar",
  "fiquei_ansioso",
  "nao_tive_energia",
  "nao_queria_enfrentar",
  "me_distrai",
  "nao_tive_tempo",
  "tarefa_grande_demais",
  "prioridade_mudou",
  "outro",
];

export const AUDIT_ACTION_LABELS: Record<AuditAction, string> = {
  login: "Login na conta",
  password_change: "Troca de senha",
  invite_sent: "Convite enviado a uma pessoa de confiança",
  permission_granted: "Permissão concedida",
  permission_revoked: "Permissão revogada",
  external_observation_recorded: "Observação registrada por pessoa de confiança",
  restricted_data_access_denied: "Tentativa de acesso negada",
  plan_changed: "Plano pessoal alterado",
  critical_alert: "Estado mudou para vermelho",
  data_exported: "Dados exportados",
  account_deletion_requested: "Conta desativada",
};
