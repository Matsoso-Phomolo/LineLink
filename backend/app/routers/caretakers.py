import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_password_hash
from app.database import get_db
from app.dependencies import get_actor_landlord_id, require_roles
from app.identity import next_identifier
from app.models import Caretaker, User, UserRole
from app.ownership import assert_landlord_access, scoped_query
from app.schemas import (
    CaretakerAccountCreate,
    CaretakerRead,
    CaretakerUpdate,
)

router = APIRouter(prefix="/caretakers", tags=["caretakers"])


def caretaker_read(caretaker: Caretaker) -> dict:
    return {
        "id": caretaker.id,
        "user_id": caretaker.user_id,
        "landlord_id": caretaker.landlord_id,
        "phone": caretaker.phone,
        "username": caretaker.user.username,
        "full_name": caretaker.user.full_name,
        "email": caretaker.user.email,
        "is_active": caretaker.user.is_active,
        "created_at": caretaker.created_at,
    }


@router.post("", response_model=CaretakerRead)
def create_caretaker(
    payload: CaretakerAccountCreate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.national_admin, UserRole.landlord)
    ),
):
    landlord_id = get_actor_landlord_id(db, user)

    if not landlord_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin-created caretakers require a landlord context.",
        )

    assert_landlord_access(db, user, landlord_id)

    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )

    caretaker_user = User(
        email=str(payload.email),
        username=next_identifier(db, UserRole.caretaker),
        phone=payload.phone,
        full_name=payload.full_name,
        role=UserRole.caretaker,
        hashed_password=get_password_hash(payload.password),
        must_change_password=True,
    )

    db.add(caretaker_user)
    db.flush()

    caretaker = Caretaker(
        user_id=caretaker_user.id,
        landlord_id=landlord_id,
        phone=payload.phone,
    )

    db.add(caretaker)
    db.commit()
    db.refresh(caretaker)

    return caretaker_read(caretaker)


@router.get("", response_model=list[CaretakerRead])
def list_caretakers(
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.national_admin,
            UserRole.district_admin,
            UserRole.landlord,
            UserRole.caretaker,
        )
    ),
):
    caretakers = (
        scoped_query(db, user, Caretaker)
        .order_by(Caretaker.created_at.desc())
        .all()
    )

    return [caretaker_read(caretaker) for caretaker in caretakers]


@router.put("/{caretaker_id}", response_model=CaretakerRead)
def update_caretaker(
    caretaker_id: uuid.UUID,
    payload: CaretakerUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.national_admin,
            UserRole.district_admin,
            UserRole.landlord,
        )
    ),
):
    caretaker = (
        scoped_query(db, user, Caretaker)
        .filter(Caretaker.id == caretaker_id)
        .first()
    )

    if not caretaker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caretaker not found",
        )

    if (
        payload.email
        and payload.email != caretaker.user.email
        and db.query(User).filter(User.email == payload.email).first()
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )

    if payload.full_name is not None:
        caretaker.user.full_name = payload.full_name

    if payload.email is not None:
        caretaker.user.email = str(payload.email)

    if payload.phone is not None:
        caretaker.user.phone = payload.phone
        caretaker.phone = payload.phone

    if payload.is_active is not None:
        caretaker.user.is_active = payload.is_active

    db.commit()
    db.refresh(caretaker)

    return caretaker_read(caretaker)


@router.delete("/{caretaker_id}")
def delete_caretaker(
    caretaker_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(
        require_roles(
            UserRole.national_admin,
            UserRole.district_admin,
            UserRole.landlord,
        )
    ),
):
    caretaker = (
        scoped_query(db, user, Caretaker)
        .filter(Caretaker.id == caretaker_id)
        .first()
    )

    if not caretaker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caretaker not found",
        )

    caretaker.user.is_active = False

    db.delete(caretaker)

    db.commit()

    return {
        "detail": "Caretaker removed and account disabled"
    }
