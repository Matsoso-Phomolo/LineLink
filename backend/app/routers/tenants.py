import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.audit import log_action
from app.auth import get_password_hash
from app.database import get_db
from app.dependencies import get_actor_landlord_id, get_current_user, require_roles
from app.identity import first_name_password, next_identifier
from app.notification_channels import send_login_credentials
from app.models import AuditAction, Occupancy, OccupancyStatus, OnboardingChecklist, RoomListing, RoomStatus, ListingStatus, Tenant, TenantStatus, User, UserRole
from app.ownership import assert_landlord_access, get_room_in_scope, get_tenant_in_scope, landlord_scope_filter
from app.rent_logic import generate_initial_rent_due
from app.schemas import TenantAccountCreate, TenantAccountResult, TenantCreate, TenantRead, TenantUpdate

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantRead)
def create_tenant(payload: TenantCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    landlord_id = get_actor_landlord_id(db, user)
    assert_landlord_access(db, user, landlord_id)
    tenant = Tenant(**payload.model_dump(), landlord_id=landlord_id)
    db.add(tenant)
    db.flush()
    db.add(OnboardingChecklist(tenant_id=tenant.id))
    log_action(db, AuditAction.create_tenant, user, landlord_id, "Tenant", tenant.id)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.post("/accounts", response_model=TenantAccountResult)
def create_tenant_account(payload: TenantAccountCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.landlord, UserRole.caretaker))):
    landlord_id = get_actor_landlord_id(db, user)
    if not landlord_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No landlord context available")
    email = str(payload.email) if payload.email else f"{next_identifier(db, UserRole.tenant).lower()}@tenant.linelink.local"
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant email already exists")
    temporary_password = first_name_password(payload.full_name)
    tenant_user = User(
        email=email,
        username=next_identifier(db, UserRole.tenant),
        phone=payload.phone,
        full_name=payload.full_name,
        role=UserRole.tenant,
        hashed_password=get_password_hash(temporary_password),
        must_change_password=True,
    )
    db.add(tenant_user)
    db.flush()
    tenant_data = payload.model_dump(exclude={"room_id", "lease_start_date", "lease_end_date", "monthly_rent", "deposit_amount"})
    tenant = Tenant(
        **tenant_data,
        user_id=tenant_user.id,
        landlord_id=landlord_id,
        lease_start_date=payload.lease_start_date,
        lease_end_date=payload.lease_end_date,
        monthly_rent=payload.monthly_rent,
        deposit_amount=payload.deposit_amount,
        outstanding_balance=payload.monthly_rent or 0,
    )
    db.add(tenant)
    db.flush()
    db.add(OnboardingChecklist(tenant_id=tenant.id, documents_submitted=False, room_assigned=bool(payload.room_id)))
    if payload.room_id:
        room = get_room_in_scope(db, user, payload.room_id)
        if room.status == RoomStatus.occupied:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room is already occupied")
        monthly_rent = payload.monthly_rent or float(room.rent_price)
        deposit = payload.deposit_amount if payload.deposit_amount is not None else float(room.deposit_amount)
        occupancy = Occupancy(
            landlord_id=landlord_id,
            tenant_id=tenant.id,
            room_id=room.id,
            move_in_date=payload.lease_start_date or date.today(),
            monthly_rent=monthly_rent,
            deposit_amount=deposit,
            billing_start_month=payload.lease_start_date or date.today(),
            status=OccupancyStatus.active,
        )
        db.add(occupancy)
        db.flush()
        room.status = RoomStatus.occupied
        db.query(RoomListing).filter(RoomListing.room_id == room.id, RoomListing.status == ListingStatus.published).update({"status": ListingStatus.rented, "is_public": False})
        generate_initial_rent_due(db, occupancy)
    send_login_credentials(tenant_user, temporary_password)
    log_action(db, AuditAction.create_tenant, user, landlord_id, "Tenant", tenant.id)
    db.commit()
    db.refresh(tenant)
    return {"tenant": tenant, "username": tenant_user.username, "temporary_password": temporary_password}


@router.get("", response_model=list[TenantRead])
def list_tenants(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == UserRole.tenant:
        return db.query(Tenant).filter(Tenant.user_id == user.id).all()
    return landlord_scope_filter(db, user, Tenant).order_by(Tenant.created_at.desc()).all()


@router.put("/{tenant_id}", response_model=TenantRead)
def update_tenant(tenant_id: uuid.UUID, payload: TenantUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tenant = get_tenant_in_scope(db, user, tenant_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(tenant, key, value)
    log_action(db, AuditAction.update_tenant, user, tenant.landlord_id, "Tenant", tenant.id)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.delete("/{tenant_id}")
def remove_tenant(tenant_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.landlord, UserRole.caretaker))):
    tenant = get_tenant_in_scope(db, user, tenant_id)
    tenant.tenant_status = TenantStatus.disabled
    if tenant.user:
        tenant.user.is_active = False
    for occupancy in db.query(Occupancy).filter(Occupancy.tenant_id == tenant.id, Occupancy.status == OccupancyStatus.active).all():
        occupancy.status = OccupancyStatus.ended
    db.commit()
    return {"detail": "Tenant disabled and active tenancy terminated"}
