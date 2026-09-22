"""
Todos os enums do domínio, centralizados aqui para evitar dois
lugares no código descrevendo o mesmo conjunto de valores válidos.

Regra: nenhum destes enums representa um julgamento clínico. São
categorias operacionais (o que a pessoa registrou / o que o sistema
observou), nunca um rótulo diagnóstico (ver docs/architecture.md,
seção 6).
"""
import enum


class ToneStyle(str, enum.Enum):
    """Item do documento: tom de interface escolhido no onboarding."""
    QUASE_VAZIO = "quase_vazio"
    COMPANHEIRO_CALMO = "companheiro_calmo"


class RelationshipStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"


class PermissionKey(str, enum.Enum):
    """Item 14/51 do documento — permissões concedíveis a uma pessoa de confiança."""
    RECORD_OBSERVATION = "record_observation"
    SUGGEST_TASK = "suggest_task"
    CREATE_TASK = "create_task"
    HELP_WITH_TASK = "help_with_task"
    CONFIRM_EVENT = "confirm_event"
    REQUEST_CHECKIN = "request_checkin"
    RECEIVE_ALERT_YELLOW = "receive_alert_yellow"
    RECEIVE_ALERT_RED = "receive_alert_red"
    VIEW_ROUTINE = "view_routine"
    VIEW_MEDICATION = "view_medication"
    VIEW_SPECIFIC_INDICATORS = "view_specific_indicators"
    VIEW_FULL_HISTORY = "view_full_history"
    ACCESS_CRISIS_PLAN = "access_crisis_plan"


class ActivationDomain(str, enum.Enum):
    """Item 11 — motor de ativação: usuário escolhe quais fazem sentido pra ele."""
    LEVANTAR = "levantar"
    HIGIENE = "higiene"
    ALIMENTACAO = "alimentacao"
    SAIR_DE_CASA = "sair_de_casa"
    CAMINHAR = "caminhar"
    ATIVIDADE_FISICA = "atividade_fisica"
    LAZER = "lazer"
    INTERACAO_SOCIAL = "interacao_social"
    TRABALHO = "trabalho"
    ESTUDO = "estudo"
    ATIVIDADE_SIGNIFICATIVA = "atividade_significativa"
    TAREFAS_BASICAS = "tarefas_basicas"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    STARTED = "started"
    PAUSED = "paused"
    POSTPONED = "postponed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskOrigin(str, enum.Enum):
    """Item 25 — diferenciar tarefa do usuário de sugestão externa."""
    SELF = "self"
    TRUSTED_PERSON_SUGGESTION = "trusted_person_suggestion"


class TaskEventType(str, enum.Enum):
    """Item 33 — arquitetura de eventos, nunca sobrescrever status direto."""
    CREATED = "created"
    STARTED = "started"
    PAUSED = "paused"
    POSTPONED = "postponed"
    RESUMED = "resumed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskFailureReasonType(str, enum.Enum):
    """Item 8 — motivos pré-definidos + 'outro' com texto livre."""
    ESQUECI = "esqueci"
    NAO_CONSEGUI_COMECAR = "nao_consegui_comecar"
    FIQUEI_ANSIOSO = "fiquei_ansioso"
    NAO_TIVE_ENERGIA = "nao_tive_energia"
    NAO_QUERIA_ENFRENTAR = "nao_queria_enfrentar"
    ME_DISTRAI = "me_distrai"
    NAO_TIVE_TEMPO = "nao_tive_tempo"
    TAREFA_GRANDE_DEMAIS = "tarefa_grande_demais"
    PRIORIDADE_MUDOU = "prioridade_mudou"
    OUTRO = "outro"


class MedicationEventStatus(str, enum.Enum):
    TAKEN = "taken"
    NOT_TAKEN = "not_taken"
    FORGOT_TO_CONFIRM = "forgot_to_confirm"
    SKIPPED_DELIBERATELY = "skipped_deliberately"
    UNAVAILABLE = "unavailable"


class MedicationSkipReason(str, enum.Enum):
    """Item 13 — apenas informação de adesão, nunca instrução de dose."""
    ESQUECI = "esqueci"
    ROTINA_MUDOU = "rotina_mudou"
    NAO_CONSEGUI_LEVANTAR = "nao_consegui_levantar"
    EFEITO_ADVERSO = "efeito_adverso"
    MEDO = "medo"
    MEDICAMENTO_INDISPONIVEL = "medicamento_indisponivel"
    DECISAO_PROPRIA = "decisao_propria"
    OUTRO = "outro"


class ObservationCategory(str, enum.Enum):
    """Item 15."""
    ISOLAMENTO = "isolamento"
    AUSENCIA_TRABALHO = "ausencia_trabalho"
    AUSENCIA_ESTUDOS = "ausencia_estudos"
    MUDANCA_SONO = "mudanca_sono"
    AUTOCUIDADO_REDUZIDO = "autocuidado_reduzido"
    COMUNICACAO_REDUZIDA = "comunicacao_reduzida"
    MUDANCA_INCOMUM = "mudanca_incomum"
    IRRITABILIDADE = "irritabilidade"
    DIFICULDADE_FUNCIONAR = "dificuldade_funcionar"
    AUSENCIA = "ausencia"
    OUTRO = "outro"


class ObservationSince(str, enum.Enum):
    HOJE = "hoje"
    DOIS_A_TRES_DIAS = "2_3_dias"
    MAIS_DE_TRES_DIAS = "mais_de_3_dias"


class ObservationIntensity(str, enum.Enum):
    LEVE = "leve"
    RELEVANTE = "relevante"
    SERIA = "seria"


class IndicatorKey(str, enum.Enum):
    """
    Série normalizada que alimenta o motor de baseline/desvio.
    Cada indicador é escrito por um serviço de ingestão específico
    (check-in, eventos de tarefa, rotina, observação, medicação) — a
    tabela FunctionalIndicator não sabe de onde veio o dado, só sabe
    o valor normalizado do dia.
    """
    SLEEP_HOURS = "sleep_hours"
    WAKE_TIME_MINUTES = "wake_time_minutes"
    SLEEP_TIME_MINUTES = "sleep_time_minutes"
    SLEEP_QUALITY = "sleep_quality"
    MOOD = "mood"
    ENERGY = "energy"
    ANXIETY = "anxiety"
    ABILITY_TO_START_TASKS = "ability_to_start_tasks"
    TASKS_STARTED_COUNT = "tasks_started_count"
    TASKS_POSTPONED_COUNT = "tasks_postponed_count"
    TASKS_COMPLETED_COUNT = "tasks_completed_count"
    LEFT_HOME = "left_home"
    SOCIAL_CONTACT = "social_contact"
    ACTIVITY_LEVEL = "activity_level"
    AVOIDANCE_LOAD = "avoidance_load"
    MEDICATION_ADHERENCE = "medication_adherence"


class IndicatorSource(str, enum.Enum):
    CHECKIN = "checkin"
    TASK_EVENT = "task_event"
    ROUTINE = "routine"
    OBSERVATION = "observation"
    MEDICATION_EVENT = "medication_event"
    DERIVED = "derived"


class BaselineSource(str, enum.Enum):
    """Item da sessão anterior: baseline híbrido (autodeclarado x observado)."""
    SELF_DECLARED = "self_declared"
    OBSERVED = "observed"
    HYBRID = "hybrid"


class BaselineStatus(str, enum.Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"


class DeviationEngine(str, enum.Enum):
    """Item 9-12 — motores separados, nunca índice único."""
    EXECUTIVE = "executive"
    AVOIDANCE = "avoidance"
    ACTIVATION = "activation"
    STABILITY = "stability"


class AlertState(str, enum.Enum):
    """Item 20 — nunca inventar limiar clínico, regras transparentes e configuráveis."""
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class InterventionType(str, enum.Enum):
    MICROINTERVENTION = "microintervention"
    BODY_DOUBLING_SESSION = "body_doubling_session"


class InterventionStatus(str, enum.Enum):
    SUGGESTED = "suggested"
    REQUESTED = "requested"
    ACCEPTED = "accepted"
    STARTED = "started"
    FINISHED = "finished"
    DISMISSED = "dismissed"


class PersonalPlanSignal(str, enum.Enum):
    """Item 19 — sinais que o usuário define previamente, período estável."""
    FALTAS = "faltas"
    ISOLAMENTO = "isolamento"
    SONO = "sono"
    MEDICACAO = "medicacao"
    ABANDONO_DE_TAREFAS = "abandono_de_tarefas"
    USO_DE_SUBSTANCIAS = "uso_de_substancias"
    COMUNICACAO = "comunicacao"
    AUTOCUIDADO = "autocuidado"


class NotificationType(str, enum.Enum):
    REMINDER = "reminder"
    CHECKIN_REQUEST = "checkin_request"
    TASK = "task"
    SUPPORT_REQUEST = "support_request"
    OBSERVATION = "observation"
    RELEVANT_CHANGE = "relevant_change"
    ALERT = "alert"


class NotificationChannel(str, enum.Enum):
    PUSH = "push"
    EMAIL = "email"
    IN_APP = "in_app"


class NotificationPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LifeEventType(str, enum.Enum):
    """Item 57."""
    TRAVEL = "travel"
    VACATION = "vacation"
    NEW_JOB = "new_job"
    ILLNESS = "illness"
    MOVE = "move"
    OTHER = "other"


class AuditAction(str, enum.Enum):
    """Item 31."""
    LOGIN = "login"
    PASSWORD_CHANGE = "password_change"
    INVITE_SENT = "invite_sent"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"
    EXTERNAL_OBSERVATION_RECORDED = "external_observation_recorded"
    RESTRICTED_DATA_ACCESS_DENIED = "restricted_data_access_denied"
    PLAN_CHANGED = "plan_changed"
    CRITICAL_ALERT = "critical_alert"
    DATA_EXPORTED = "data_exported"
    ACCOUNT_DELETION_REQUESTED = "account_deletion_requested"
    SUSPECTED_SESSION_THEFT = "suspected_session_theft"
    ACCOUNT_DELETED = "account_deleted"
