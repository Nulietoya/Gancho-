"""
Envio de e-mail (ETAPA 22) — o "provedor ainda não conectado" citado
desde a ETAPA 6 (cadastro sem verificação, reset de senha sem envio
real). Abstração mínima de propósito: sem `smtp_host` configurado
(nenhum valor default nas variáveis de ambiente do projeto), cai num
backend de log — dá pra testar o fluxo inteiro (token gerado, e-mail
"enviado", conteúdo correto) sem depender de credencial real nem em
desenvolvimento nem nos testes automatizados. Configurar as variáveis
`SMTP_*` no `.env` liga o envio de verdade via SMTP padrão da
biblioteca padrão do Python — nenhum código de quem chama
`send_email` muda quando isso acontece.
"""
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger("gancho.email")


def send_email(to_email: str, subject: str, body: str) -> None:
    settings = get_settings()

    if not settings.smtp_host:
        # WARNING, não INFO: o nível padrão de log em Python (e o do
        # próprio uvicorn) filtra INFO por padrão — um e-mail
        # "simulado" que ninguém consegue ver no log não serve nem
        # como fallback de desenvolvimento (esse era exatamente o
        # ponto de logar em vez de silenciosamente descartar).
        logger.warning("[e-mail simulado — SMTP não configurado] para=%s assunto=%r\n%s", to_email, subject, body)
        return

    message = EmailMessage()
    message["From"] = settings.smtp_from_email or "no-reply@gancho.app"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)
