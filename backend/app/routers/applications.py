import uuid
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import require_roles
from app.models import ApplicationStatus, RequestResponseLog, TenantApplication, User, UserRole
from app.request_response import log_request_response
from app.routers.listings import assign_application_room, listing_in_scope
from app.ownership import landlord_scope_filter
from app.schemas import ApplicationAssignRoom, ApplicationDecision, ApplicationFormLink, RequestResponseLogRead, TenantApplicationRead

router = APIRouter(prefix="/applications", tags=["applications"])


def application_in_scope(db: Session, user: User, application_id: uuid.UUID) -> TenantApplication:
    application = db.get(TenantApplication, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    listing_in_scope(db, user, application.listing_id)
    return application


@router.get("", response_model=list[TenantApplicationRead])
def list_applications(db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    query = landlord_scope_filter(db, user, TenantApplication)
    return query.order_by(TenantApplication.created_at.desc()).all()


@router.put("/{application_id}/approve", response_model=TenantApplicationRead)
def approve_application(application_id: uuid.UUID, payload: ApplicationDecision, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    application = application_in_scope(db, user, application_id)
    application.status = ApplicationStatus.approved
    application.landlord_note = payload.landlord_note
    db.commit()
    db.refresh(application)
    return application


@router.put("/{application_id}/accept", response_model=TenantApplicationRead)
def accept_room_request(application_id: uuid.UUID, payload: ApplicationDecision, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    application = application_in_scope(db, user, application_id)
    listing = listing_in_scope(db, user, application.listing_id)
    application.status = ApplicationStatus.accepted
    application.landlord_note = payload.landlord_note
    if application.preferred_response_method:
        message = payload.landlord_note or f"Your room request for {listing.room.room_number if listing.room else 'this room'} at {listing.listing_property.name if listing.listing_property else listing.location_area} has been accepted. Please follow the next instructions from the landlord/caretaker."
        log_request_response(db, application, application.preferred_response_method, message, user)
    db.commit()
    db.refresh(application)
    return application


@router.put("/{application_id}/reject", response_model=TenantApplicationRead)
def reject_application(application_id: uuid.UUID, payload: ApplicationDecision, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    application = application_in_scope(db, user, application_id)
    listing = listing_in_scope(db, user, application.listing_id)
    application.status = ApplicationStatus.rejected
    application.landlord_note = payload.landlord_note
    if application.preferred_response_method:
        message = payload.landlord_note or f"Your room request for {listing.room.room_number if listing.room else 'this room'} at {listing.listing_property.name if listing.listing_property else listing.location_area} was not accepted. You may continue searching for other available rooms on LineLink."
        log_request_response(db, application, application.preferred_response_method, message, user)
    db.commit()
    db.refresh(application)
    return application


@router.post("/{application_id}/request-info", response_model=TenantApplicationRead)
def request_application_info(application_id: uuid.UUID, payload: ApplicationDecision, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    application = application_in_scope(db, user, application_id)
    application.status = ApplicationStatus.info_requested
    application.landlord_note = payload.landlord_note
    db.commit()
    db.refresh(application)
    return application


@router.post("/{application_id}/send-form-link", response_model=ApplicationFormLink)
def send_application_form_link(application_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    application = application_in_scope(db, user, application_id)
    token = secrets.token_urlsafe(32)
    while db.query(TenantApplication).filter(TenantApplication.application_token == token).first():
        token = secrets.token_urlsafe(32)
    application.application_token = token
    application.form_sent_at = datetime.now(timezone.utc)
    application.token_expires_at = application.form_sent_at + timedelta(days=settings.application_token_expire_days)
    application.status = ApplicationStatus.form_sent
    if application.preferred_response_method:
        base_url = settings.public_base_url.rstrip("/")
        log_request_response(db, application, application.preferred_response_method, f"Please complete your LineLink room application using this secure link: {base_url}/#/apply/{token}", user)
    db.commit()
    db.refresh(application)
    base_url = settings.public_base_url.rstrip("/")
    return ApplicationFormLink(application_id=application.id, application_url=f"{base_url}/#/apply/{token}", token_expires_at=application.token_expires_at)


@router.put("/{application_id}/mark-contacted", response_model=TenantApplicationRead)
def mark_request_contacted(application_id: uuid.UUID, payload: ApplicationDecision, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    application = application_in_scope(db, user, application_id)
    application.status = ApplicationStatus.contacted
    application.landlord_note = payload.landlord_note
    if application.preferred_response_method:
        log_request_response(db, application, application.preferred_response_method, payload.landlord_note or "Contact logged by landlord/caretaker.", user)
    db.commit()
    db.refresh(application)
    return application


@router.get("/{application_id}/response-logs", response_model=list[RequestResponseLogRead])
def application_response_logs(application_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    application = application_in_scope(db, user, application_id)
    return db.query(RequestResponseLog).filter(RequestResponseLog.request_id == application.id).order_by(RequestResponseLog.created_at.desc()).all()


@router.post("/{application_id}/assign-room")
def assign_room(application_id: uuid.UUID, payload: ApplicationAssignRoom, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    return assign_application_room(application_id, payload, db, user)
