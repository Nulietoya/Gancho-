"""
Fiação do APScheduler (ETAPA 22) — nunca testado por unidade, mesma
categoria de `app/main.py`: toda a lógica de negócio mora em
`app/services/scheduler_service.py`, testável com o mesmo padrão
transacional do resto da suíte. Cada disparo abre a própria sessão de
banco (`BackgroundScheduler` roda fora do ciclo de vida de uma
requisição HTTP, não tem `get_db` de quem depender) e fecha ao final,
sucesso ou erro — nunca deixa uma sessão pendurada entre disparos.
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.database import SessionLocal
from app.services import scheduler_service

logger = logging.getLogger("gancho.scheduler")

_scheduler: BackgroundScheduler | None = None


def _run_nightly_cycle() -> None:
    db = SessionLocal()
    try:
        summary = scheduler_service.run_nightly_cycle(db)
        logger.info("ciclo noturno concluído: %s", summary)
    except Exception:
        logger.exception("falha no ciclo noturno (baseline/desvio/alerta/adesão)")
    finally:
        db.close()


def _run_notification_delivery() -> None:
    db = SessionLocal()
    try:
        scheduler_service.deliver_due_notifications(db)
    except Exception:
        logger.exception("falha na entrega de notificações agendadas")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    scheduler = BackgroundScheduler(timezone="UTC")
    # 3h da manhã UTC — fora do horário comercial de qualquer fuso
    # razoável que o produto atenda hoje, evita competir com uso ao
    # vivo da API.
    scheduler.add_job(_run_nightly_cycle, "cron", hour=3, minute=0, id="nightly_cycle", replace_existing=True)
    # A cada 15 minutos: entrega notificações que ficaram represadas
    # por horário silencioso ou teto diário (item 37) — "não
    # bombardear" não pode virar "nunca entregar".
    scheduler.add_job(
        _run_notification_delivery, "interval", minutes=15, id="notification_delivery", replace_existing=True
    )
    scheduler.start()
    _scheduler = scheduler
    # WARNING, não INFO: nível padrão de log filtra INFO (mesmo motivo
    # documentado em app/core/email.py) — isto é o único jeito de
    # confirmar visualmente, no log do processo, que o scheduler
    # realmente subiu.
    logger.warning("scheduler iniciado (ciclo noturno 03:00 UTC, entrega de notificações a cada 15min)")
    return scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
