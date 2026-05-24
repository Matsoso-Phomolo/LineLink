import uuid

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import AliasChoices, BaseModel, Field

from app.audit import log_action
from app.database import get_db
from app.dependencies import get_current_user
from app.models import AuditAction, SupportTicket, Tenant, TicketStatus, User, UserRole
from app.ownership import get_tenant_in_scope, landlord_scope_filter

router = APIRouter(prefix="/support-tickets", tags=["support tickets"])


class SupportTicketCreate(BaseModel):
    tenant_id: uuid.UUID
    title: str = Field(validation_alias=AliasChoices("title", "subject"))
    category: str
    priority: str | None = None
    description: str


class SupportTicketUpdate(BaseModel):
    status: TicketStatus | None = None
    priority: str | None = None
    assigned_to_user_id: uuid.UUID | None = None


@router.post("")
def create_ticket(payload: SupportTicketCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tenant = get_tenant_in_scope(db, user, payload.tenant_id)
    ticket = SupportTicket(landlord_id=tenant.landlord_id, **payload.model_dump())
    db.add(ticket)
    log_action(db, AuditAction.create_support_ticket, user, tenant.landlord_id, "SupportTicket")
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("")
def list_tickets(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == UserRole.tenant:
        tenant = db.query(Tenant).filter(Tenant.user_id == user.id).first()
        if not tenant:
            return []
        return db.query(SupportTicket).filter(SupportTicket.tenant_id == tenant.id).order_by(SupportTicket.created_at.desc()).all()
    return landlord_scope_filter(db, user, SupportTicket).order_by(SupportTicket.created_at.desc()).all()


@router.put("/{ticket_id}")
def update_ticket(ticket_id: uuid.UUID, payload: SupportTicketUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ticket = db.get(SupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found")
    if user.role == UserRole.tenant:
        get_tenant_in_scope(db, user, ticket.tenant_id)
    else:
        landlord_scope_filter(db, user, SupportTicket).filter(SupportTicket.id == ticket_id).one()
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(ticket, key, value)
    if payload.status == TicketStatus.resolved:
        ticket.resolved_at = datetime.now(timezone.utc)
    log_action(db, AuditAction.update_support_ticket, user, ticket.landlord_id, "SupportTicket", ticket.id)
    db.commit()
    db.refresh(ticket)
    return ticket
