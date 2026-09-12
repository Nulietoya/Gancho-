"""
Exceções de domínio da autenticação. Ficam fora de app/api para que
app/services nunca precise importar FastAPI/HTTPException — services
descrevem regra de negócio, a tradução pra HTTP é responsabilidade só
da camada de rota.
"""


class AuthError(Exception):
    """Base de todas as exceções de autenticação."""


class EmailAlreadyRegistered(AuthError):
    pass


class InvalidCredentials(AuthError):
    pass


class AccountLocked(AuthError):
    def __init__(self, locked_until):
        self.locked_until = locked_until
        super().__init__(f"conta temporariamente bloqueada até {locked_until.isoformat()}")


class AccountInactive(AuthError):
    pass


class InvalidRefreshToken(AuthError):
    pass


class RefreshTokenReused(InvalidRefreshToken):
    """
    Um refresh token já revogado (rotacionado, deslogado, ou invalidado
    por troca de senha) foi apresentado de novo. Diferente de um token
    simplesmente inválido/expirado, isso é sinal de possível cópia
    roubada em uso — o dono legítimo já trocou esse token por um novo
    e não deveria mais possuir o antigo. Subclasse de
    InvalidRefreshToken de propósito: a rota trata ambos como o mesmo
    401 genérico pro cliente (não convém confirmar pro possível
    atacante que a detecção disparou), mas o serviço já reagiu
    revogando toda sessão do usuário antes de levantar esta exceção.
    """
    pass


class InvalidResetToken(AuthError):
    pass


class ProfileError(Exception):
    """Base de exceções do perfil/onboarding (ETAPA 8/9)."""


class ProfileNotFound(ProfileError):
    pass


class ProfileAlreadyExists(ProfileError):
    pass


class TaskError(Exception):
    """Base de exceções de tarefas/eventos de tarefa (ETAPA 10)."""


class TaskNotFound(TaskError):
    pass


class InvalidTaskTransition(TaskError):
    def __init__(self, current_status, action):
        self.current_status = current_status
        self.action = action
        super().__init__(f"não é possível '{action}' uma tarefa no estado '{current_status}'")


class CheckInError(Exception):
    """Base de exceções de check-in diário (ETAPA 11)."""


class CheckInNotFound(CheckInError):
    pass


class CheckInAlreadyExists(CheckInError):
    pass


class RoutineError(Exception):
    """Base de exceções de rotina de referência (ETAPA 12)."""


class RoutineNotFound(RoutineError):
    pass


class RoutineAlreadyExists(RoutineError):
    pass


class MedicationError(Exception):
    """Base de exceções de medicamentos/adesão (ETAPA 13)."""


class MedicationNotFound(MedicationError):
    pass


class ScheduleNotFound(MedicationError):
    pass


class BaselineError(Exception):
    """Base de exceções do motor de baseline (ETAPA 17)."""


class BaselineNotFound(BaselineError):
    pass


class NoIndicatorData(BaselineError):
    pass


class DeviationEventNotFound(Exception):
    """ETAPA 18 — evento de desvio não encontrado (ou não pertence a este usuário)."""


class AlertError(Exception):
    """Base de exceções de estado/alerta (ETAPA 19)."""


class AlertNotFound(AlertError):
    pass


class InterventionError(Exception):
    """Base de exceções de intervenções (ETAPA 21)."""


class InterventionNotFound(InterventionError):
    pass


class InvalidInterventionTransition(InterventionError):
    def __init__(self, current_status, action):
        self.current_status = current_status
        self.action = action
        super().__init__(f"não é possível '{action}' uma intervenção no estado '{current_status}'")


class NotificationError(Exception):
    """Base de exceções de notificações (ETAPA 22)."""


class NotificationNotFound(NotificationError):
    pass


class PersonalPlanError(Exception):
    """Base de exceções do plano pessoal (ETAPA 25, item 19 — "plano quando eu não perceber")."""


class PersonalPlanNotFound(PersonalPlanError):
    pass


class PersonalPlanAlreadyExists(PersonalPlanError):
    pass


class PersonalPlanRuleNotFound(PersonalPlanError):
    pass


class AccountError(Exception):
    """Base de exceções de ciclo de vida da conta (ETAPA 25, item 53 — LGPD)."""


class InvalidAccountPassword(AccountError):
    pass


class AuthorizationError(Exception):
    """Base de exceções da camada de autorização (item 36: 'o que pode fazer')."""


class RelationshipNotFound(AuthorizationError):
    pass


class InvalidInviteToken(AuthorizationError):
    pass


class PermissionDenied(AuthorizationError):
    def __init__(self, permission_key):
        self.permission_key = permission_key
        super().__init__(f"permissão '{permission_key}' não concedida para este relacionamento")
