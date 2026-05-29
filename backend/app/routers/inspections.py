import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.audit import log_action
from app.database import get_db
from app.dependencies import require_roles
from app.models import (
    AuditAction,
    DamageRecord,
    DamageStatus,
    InspectionStatus,
    RoomInspection,
    User,
    UserRole,
)
from app.ownership import get_room_in_scope, scoped_query
from app.schemas import (
    DamageRecordCreate,
    DamageRecordRead,
    RoomInspectionCreate,
    RoomInspectionRead,
)

router = APIRouter(prefix="/inspections", tags=["inspections"])


def inspection_in_scope(
    db: Session,
    user: User,
    inspection_id: uuid.UUID,
) -> RoomInspection:
    inspection = (
        scoped_query(db, user, RoomInspection)
        .filter(RoomInspection.id == inspection_id)
        .first()
    )

    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found",
        )

    return inspection


def damage_in_scope(
    db: Session,
    user: User,
    damage_id: uuid.UUID,
) -> DamageRecord:
    damage = (
        scoped_query(db, user, DamageRecord)
        .filter(DamageRecord.id == damage_id)
        .first()
    )

    if not damage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Damage record not found",
        )

    return damage


@router.post("", response_model=RoomInspectionRead)
def create_inspection(
    payload: RoomInspectionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    room = get_room_in_scope(db, user, payload.room_id)

    inspection = RoomInspection(
        landlord_id=room.landlord_id,
        **payload.model_dump(),
    )

    db.add(inspection)
    db.commit()
    db.refresh(inspection)

    return inspection


@router.get("", response_model=list[RoomInspectionRead])
def list_inspections(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    return (
        scoped_query(db, user, RoomInspection)
        .order_by(RoomInspection.created_at.desc())
        .all()
    )


@router.post("/{inspection_id}/complete", response_model=RoomInspectionRead)
def complete_inspection(
    inspection_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    inspection = inspection_in_scope(db, user, inspection_id)

    inspection.status = InspectionStatus.completed
    inspection.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(inspection)

    return inspection


@router.post("/damages", response_model=DamageRecordRead)
def create_damage(
    payload: DamageRecordCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    room = get_room_in_scope(db, user, payload.room_id)

    damage = DamageRecord(
        landlord_id=room.landlord_id,
        **payload.model_dump(),
    )

    db.add(damage)

    log_action(
        db,
        AuditAction.create_damage_record,
        user,
        room.landlord_id,
        "DamageRecord",
    )

    db.commit()
    db.refresh(damage)

    return damage


@router.get("/damages", response_model=list[DamageRecordRead])
def list_damages(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    return (
        scoped_query(db, user, DamageRecord)
        .order_by(DamageRecord.created_at.desc())
        .all()
    )


@router.put("/damages/{damage_id}/{damage_status}", response_model=DamageRecordRead)
def update_damage_status(
    damage_id: uuid.UUID,
    damage_status: DamageStatus,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    damage = damage_in_scope(db, user, damage_id)

    damage.status = damage_status

    db.commit()
    db.refresh(damage)

    return damage
