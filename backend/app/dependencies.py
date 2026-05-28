import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth import decode_token
from app.database import get_db
from app.models import (
    Caretaker,
    DistrictAdminAssignment,
    Landlord,
    Tenant,
    User,
    UserRole,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_token(token)

    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    user = db.get(User, uuid.UUID(payload["sub"]))

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive or missing user",
        )

    return user


def require_roles(*roles: UserRole) -> Callable:
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current_user

    return checker


def is_national_admin(user: User) -> bool:
    return user.role == UserRole.admin


def is_district_admin(user: User) -> bool:
    return user.role == UserRole.district_admin


def get_district_admin_district_ids(
    db: Session,
    user: User,
) -> list[uuid.UUID]:
    if not is_district_admin(user):
        return []

    rows = (
        db.query(DistrictAdminAssignment)
        .filter(
            DistrictAdminAssignment.user_id == user.id,
            DistrictAdminAssignment.is_active.is_(True),
        )
        .all()
    )

    return [row.district_id for row in rows]


def get_primary_district_admin_district_id(
    db: Session,
    user: User,
) -> uuid.UUID | None:
    district_ids = get_district_admin_district_ids(db, user)

    return district_ids[0] if district_ids else None


def assert_district_admin_access(
    db: Session,
    user: User,
    district_id: uuid.UUID | None,
) -> None:
    if is_national_admin(user):
        return

    if not is_district_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="District admin access required",
        )

    if not district_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="District context is required",
        )

    district_ids = get_district_admin_district_ids(db, user)

    if district_id not in district_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your assigned district",
        )


def require_national_or_district_admin() -> Callable:
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in {
            UserRole.admin,
            UserRole.district_admin,
        }:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="National or district admin permissions required",
            )

        return current_user

    return checker


def get_actor_landlord_id(
    db: Session,
    user: User,
) -> uuid.UUID | None:
    if user.role in {UserRole.admin, UserRole.district_admin}:
        return None

    if user.role == UserRole.landlord:
        profile = db.query(Landlord).filter(Landlord.user_id == user.id).first()
        return profile.id if profile else None

    if user.role == UserRole.caretaker:
        profile = db.query(Caretaker).filter(Caretaker.user_id == user.id).first()
        return profile.landlord_id if profile else None

    if user.role == UserRole.tenant:
        profile = db.query(Tenant).filter(Tenant.user_id == user.id).first()
        return profile.landlord_id if profile else None

    return None


def current_landlord_id(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> uuid.UUID:
    landlord_id = get_actor_landlord_id(db, current_user)

    if not landlord_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No landlord context available",
        )

    return landlord_id
