import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.audit import log_action
from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.lease_logic import generate_lease_for_occupancy
from app.models import (
    AuditAction,
    LeaseAgreement,
    LeaseStatus,
    Notification,
    Occupancy,
    Tenant,
    User,
    UserRole,
)
from app.ownership import assert_landlord_access, scoped_query
from app.schemas import LeaseAgreementRead, LeaseUpdate

router = APIRouter(prefix="/leases", tags=["leases"])


def lease_in_scope(
    db: Session,
    user: User,
    lease_id: uuid.UUID,
) -> LeaseAgreement:
    lease = db.get(LeaseAgreement, lease_id)

    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lease not found",
        )

    if user.role == UserRole.tenant:
        tenant = db.query(Tenant).filter(Tenant.user_id == user.id).first()

        if not tenant or lease.tenant_id != tenant.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Lease is outside your account",
            )

        return lease

    scoped_lease = (
        scoped_query(db, user, LeaseAgreement)
        .filter(LeaseAgreement.id == lease.id)
        .first()
    )

    if not scoped_lease:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Lease is outside your scope",
        )

    return lease


@router.get("", response_model=list[LeaseAgreementRead])
def list_leases(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == UserRole.tenant:
        tenant = db.query(Tenant).filter(Tenant.user_id == user.id).first()

        if not tenant:
            return []

        return (
            db.query(LeaseAgreement)
            .filter(LeaseAgreement.tenant_id == tenant.id)
            .order_by(LeaseAgreement.created_at.desc())
            .all()
        )

    return (
        scoped_query(db, user, LeaseAgreement)
        .order_by(LeaseAgreement.created_at.desc())
        .all()
    )


@router.post("/generate/{occupancy_id}", response_model=LeaseAgreementRead)
def generate_lease(
    occupancy_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    occupancy = db.get(Occupancy, occupancy_id)

    if not occupancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Occupancy not found",
        )

    assert_landlord_access(db, user, occupancy.landlord_id)

    lease = generate_lease_for_occupancy(db, occupancy)

    db.commit()
    db.refresh(lease)

    return lease


@router.put("/{lease_id}", response_model=LeaseAgreementRead)
def update_lease(
    lease_id: uuid.UUID,
    payload: LeaseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    lease = lease_in_scope(db, user, lease_id)

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(lease, key, value)

    db.commit()
    db.refresh(lease)

    return lease


@router.post("/{lease_id}/issue", response_model=LeaseAgreementRead)
def issue_lease(
    lease_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    lease = lease_in_scope(db, user, lease_id)

    lease.status = LeaseStatus.issued
    lease.landlord_signed_at = datetime.now(timezone.utc)

    tenant = db.get(Tenant, lease.tenant_id)

    if tenant and tenant.user_id:
        db.add(
            Notification(
                user_id=tenant.user_id,
                title="Lease issued",
                body=f"Lease {lease.lease_number} is ready for review and signature.",
                category="leases",
            )
        )

    log_action(
        db,
        AuditAction.issue_lease,
        user,
        lease.landlord_id,
        "LeaseAgreement",
        lease.id,
    )

    db.commit()
    db.refresh(lease)

    return lease


@router.post("/{lease_id}/tenant-sign", response_model=LeaseAgreementRead)
def tenant_sign_lease(
    lease_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.tenant)),
):
    lease = lease_in_scope(db, user, lease_id)

    lease.tenant_signed_at = datetime.now(timezone.utc)
    lease.status = (
        LeaseStatus.active
        if lease.landlord_signed_at
        else LeaseStatus.signed
    )

    log_action(
        db,
        AuditAction.sign_lease,
        user,
        lease.landlord_id,
        "LeaseAgreement",
        lease.id,
    )

    db.commit()
    db.refresh(lease)

    return lease


@router.get("/{lease_id}/pdf")
def lease_pdf(
    lease_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    lease = lease_in_scope(db, user, lease_id)

    content = (
        f"LineLink Lease Agreement\n\n"
        f"Lease: {lease.lease_number}\n"
        f"Monthly rent: M{lease.monthly_rent}\n"
        f"Deposit: M{lease.deposit_amount}\n"
        f"Start date: {lease.start_date}\n"
        f"Terms:\n{lease.terms or ''}\n\n"
        "PDF rendering is scaffolded; provider-backed PDF generation can replace this text response."
    )

    return Response(content=content, media_type="text/plain")
