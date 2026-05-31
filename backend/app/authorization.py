from fastapi import HTTPException, status

from app.models import User, UserRole


def assert_role(user: User, *roles: UserRole) -> None:
    if user.role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


def assert_admin_or_landlord_actor(user: User) -> None:
    assert_role(user, UserRole.national_admin, UserRole.district_admin, UserRole.landlord, UserRole.caretaker)
