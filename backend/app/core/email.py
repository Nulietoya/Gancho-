"""
Envio de e-mail (ETAPA 22, revisado após o deploy real na ETAPA 35).
"Provedor ainda não conectado" citado desde a ETAPA 6 (cadastro sem
verificação, reset de senha sem envio real). Duas formas de envio
real, verificadas nesta ordem:

1. Resend (API HTTPS) — configurar `RESEND_API_KEY`. Recomendado:
   várias hospedagens (Railway incluso, nos planos Free/Trial/Hobby)
   bloqueiam SMTP de saída por completo pra evitar abuso/spam — só
   liberam no plano pago. HTTPS (porta 443) nunca é bloqueado, então
   um provedor com API HTTP é a forma que funciona em qualquer plano.
   Ver docs/deploy.md.
2. SMTP padrão — configurar `SMTP_*`. Só funciona em hospedagens/
   planos que liberam portas SMTP (25/465/587) de saída.

Sem nenhuma das duas configuradas, cai num backend de log — dá pra
testar o fluxo inteiro (token gerado, e-mail "enviado", conteúdo
correto) sem depender de credencial real nem em desenvolvimento nem
nos testes automatizados. Nenhum código de quem chama `send_email`
muda entre os três casos — e uma falha de envio (rede fora do ar,
credencial inválida, etc.) nunca propaga pra quem chamou: registro e
reset de senha continuam funcionando mesmo se o e-mail não sair, só
fica registrado no log pra investigar depois.
"""
import logging
import smtplib
from email.message import EmailMessage

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger("gancho.email")

_RESEND_API_URL = "https://api.resend.com/emails"

# Timeout de rede pras duas formas de envio real. Sem isso, uma porta
# bloqueada silenciosamente (em vez de recusada) trava a requisição
# inteira (e o worker que a atende) por tempo indefinido — foi
# exatamente o que aconteceu ao testar SMTP contra um provedor que
# bloqueia a porta na borda da rede, sem nem devolver "conexão
# recusada".
_NETWORK_TIMEOUT_SECONDS = 10.0


def send_email(to_email: str, subject: str, body: str) -> None:
    settings = get_settings()

    if settings.resend_api_key:
        _send_via_resend(settings, to_email, subject, body)
        return

    if settings.smtp_host:
        _send_via_smtp(settings, to_email, subject, body)
        return

    # WARNING, não INFO: o nível padrão de log em Python (e o do
    # próprio uvicorn) filtra INFO por padrão — um e-mail "simulado"
    # que ninguém consegue ver no log não serve nem como fallback de
    # desenvolvimento (esse era exatamente o ponto de logar em vez de
    # silenciosamente descartar).
    logger.warning(
        "[e-mail simulado — nenhum provedor configurado] para=%s assunto=%r\n%s", to_email, subject, body
    )


def _send_via_resend(settings: Settings, to_email: str, subject: str, body: str) -> None:
    # NUNCA usar `settings.smtp_from_email` aqui: é um endereço qualquer
    # (ex.: Gmail do usuário), e o Resend rejeita com 403 qualquer
    # remetente que não seja o domínio de teste deles ou um domínio
    # próprio verificado — enviar "de" um Gmail seria falsificação de
    # remetente, bloqueada por design. `resend_from_email` existe
    # justamente pra, no futuro, apontar pra um domínio verificado
    # (resend.com/domains) sem precisar mudar código nenhum.
    from_email = settings.resend_from_email or "Gancho <onboarding@resend.dev>"
    try:
        response = httpx.post(
            _RESEND_API_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={"from": from_email, "to": [to_email], "subject": subject, "text": body},
            timeout=_NETWORK_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        logger.exception("Falha ao enviar e-mail via Resend para=%s", to_email)


def _send_via_smtp(settings: Settings, to_email: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = settings.smtp_from_email or "no-reply@gancho.app"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=_NETWORK_TIMEOUT_SECONDS) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except (smtplib.SMTPException, OSError):
        logger.exception("Falha ao enviar e-mail via SMTP para=%s", to_email)
