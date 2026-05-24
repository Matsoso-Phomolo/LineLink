from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import (
    CallTaskStatus,
    PreferredResponseMethod,
    RequestCallLog,
    RequestResponseLog,
    RequestResponseStatus,
    TenantApplication,
    User,
)
from app.notification_channels import send_email, send_sms, send_whatsapp


def response_contact_value(application: TenantApplication) -> str | None:
    if application.preferred_response_method == PreferredResponseMethod.email:
        return application.email
    return application.phone


def log_request_response(db: Session, application: TenantApplication, channel: PreferredResponseMethod, message: str, actor: User | None = None) -> RequestResponseLog:
    sent_at = datetime.now(timezone.utc)
    status = RequestResponseStatus.scaffolded
    contact_value = response_contact_value(application)

    if channel == PreferredResponseMethod.email and application.email:
        send_email(application.email, "LineLink room request", message)
    elif channel == PreferredResponseMethod.whatsapp and application.phone:
        send_whatsapp(application.phone, message)
    elif channel == PreferredResponseMethod.sms and application.phone:
        send_sms(application.phone, message)
    elif channel == PreferredResponseMethod.phone_call and actor and application.phone:
        call = RequestCallLog(request_id=application.id, caller_user_id=actor.id, recipient_phone=application.phone, status=CallTaskStatus.pending_call)
        db.add(call)
        sent_at = None

    log = RequestResponseLog(
        request_id=application.id,
        recipient_name=application.full_name,
        recipient_phone=application.phone,
        recipient_email=application.email,
        channel=channel,
        message=message,
        status=status,
        sent_at=sent_at,
    )
    db.add(log)
    application.response_contact_value = contact_value
    application.response_sent_at = sent_at
    application.response_status = status
    return log

