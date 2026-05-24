from app.models import User


def send_email(to: str, subject: str, body: str) -> None:
    # Provider integration point: SendGrid, Resend, SMTP, etc.
    return None


def send_whatsapp(to: str, body: str) -> None:
    # Provider integration point: WhatsApp Business API or local gateway.
    return None


def send_sms(to: str, body: str) -> None:
    # Provider integration point: SMS aggregator.
    return None


def send_password_reset(user: User, token: str, channel: str = "email") -> None:
    message = f"LineLink password reset token: {token}. This token expires in 1 hour."
    if channel == "whatsapp" and user.phone:
        send_whatsapp(user.phone, message)
    elif channel == "sms" and user.phone:
        send_sms(user.phone, message)
    else:
        send_email(user.email, "LineLink password reset", message)


def send_login_credentials(user: User, temporary_password: str) -> None:
    message = f"Your LineLink username is {user.username}. Temporary password: {temporary_password}"
    send_email(user.email, "LineLink account created", message)
    if user.phone:
        send_sms(user.phone, message)
