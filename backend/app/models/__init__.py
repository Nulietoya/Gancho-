"""
Importar todo model aqui é o que faz `Base.metadata` (usado pelo
Alembic autogenerate) enxergar a tabela. Se um model novo for criado
e não for importado neste arquivo, ele existe em Python mas o
Alembic nunca vai gerar a migration dele — erro comum, por isso
centralizado num único lugar em vez de depender de import implícito
em outro módulo.
"""
from app.models.audit import AuditLog
from app.models.auth import PasswordResetToken, RefreshSession
from app.models.baseline import Baseline, BaselineMetric, FunctionalIndicator
from app.models.checkin import DailyCheckIn
from app.models.deviation import Alert, DeviationEvent
from app.models.intervention import Intervention, InterventionResult
from app.models.medication import Medication, MedicationEvent, MedicationSchedule
from app.models.notification import Notification, NotificationPreference
from app.models.observation import Observation
from app.models.plan import PersonalPlan, PersonalPlanRule
from app.models.routine import LifeEvent, Routine, RoutineEvent
from app.models.task import Task, TaskEvent, TaskFailureReason
from app.models.trust import Permission, TrustedPersonRelationship
from app.models.user import Profile, User

__all__ = [
    "AuditLog",
    "PasswordResetToken",
    "RefreshSession",
    "Baseline",
    "BaselineMetric",
    "FunctionalIndicator",
    "DailyCheckIn",
    "Alert",
    "DeviationEvent",
    "Intervention",
    "InterventionResult",
    "Medication",
    "MedicationEvent",
    "MedicationSchedule",
    "Notification",
    "NotificationPreference",
    "Observation",
    "PersonalPlan",
    "PersonalPlanRule",
    "LifeEvent",
    "Routine",
    "RoutineEvent",
    "Task",
    "TaskEvent",
    "TaskFailureReason",
    "Permission",
    "TrustedPersonRelationship",
    "Profile",
    "User",
]
