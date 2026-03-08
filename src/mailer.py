from __future__ import annotations

import smtplib
from email.message import EmailMessage

from .models import Settings


def create_email(
    settings: Settings,
    member_name: str,
    member_email: str,
    author: str,
    content: str,
    url: str,
) -> EmailMessage:
    body = settings.email_template.format(
        name=member_name,
        author=author,
        content=content.strip(),
        url=url,
    )

    msg = EmailMessage()
    msg["Subject"] = settings.email_subject.format(author=author)
    msg["From"] = settings.email_sender.format(email=settings.email)
    msg["To"] = member_email
    msg.set_content(body)
    return msg


def send_emails(settings: Settings, messages: list[EmailMessage]) -> None:
    if not messages:
        return

    try:
        with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.email, settings.email_password)
            for msg in messages:
                server.send_message(msg)
    except Exception as exc:
        print(f"Unable to send emails: {exc}")
