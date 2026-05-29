import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import (
    get_actor_landlord_id,
    get_district_admin_district_ids,
    is_district_admin,
    is_national_admin,
)
from app.models import Property, Room, Tenant, User, UserRole


def assert_district_access(db: Session, user: User, district_id: uuid.UUID | None) -> None:
    if is_national_admin(user):
        return

    if not district_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Resource has no district scope",
        )

    if is_district_admin(user):
        district_ids = get_district_admin_district_ids(db, user)

        if district_id not in district_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Resource is outside your district scope",
            )

        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="District-level access required",
    )


def scoped_query(db: Session, user: User, model):
    if is_national_admin(user):
        return db.query(model)

    if is_district_admin(user):
        district_ids = get_district_admin_district_ids(db, user)

        if not district_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No district scope assigned",
            )

        if hasattr(model, "district_id"):
            return db.query(model).filter(model.district_id.in_(district_ids))

        if hasattr(model, "property_id"):
            return (
                db.query(model)
                .join(Property, Property.id == model.property_id)
                .filter(Property.district_id.in_(district_ids))
            )

        if hasattr(model, "room_id"):
            return (
                db.query(model)
                .join(Room, Room.id == model.room_id)
                .join(Property, Property.id == Room.property_id)
                .filter(Property.district_id.in_(district_ids))
            )

        if hasattr(model, "landlord_id"):
            return (
                db.query(model)
                .join(Property, Property.landlord_id == model.landlord_id)
                .filter(Property.district_id.in_(district_ids))
                .distinct()
            )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Model does not support district scoping",
        )

    landlord_id = get_actor_landlord_id(db, user)

    if not landlord_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No landlord scope",
        )

    if hasattr(model, "landlord_id"):
        return db.query(model).filter(model.landlord_id == landlord_id)

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Model does not support landlord scoping",
    )


def landlord_scope_filter(db: Session, user: User, model):
    return scoped_query(db, user, model)


def assert_landlord_access(db: Session, user: User, landlord_id: uuid.UUID) -> None:
    if is_national_admin(user):
        return

    if is_district_admin(user):
        district_ids = get_district_admin_district_ids(db, user)

        landlord_property = (
            db.query(Property)
            .filter(
                Property.landlord_id == landlord_id,
                Property.district_id.in_(district_ids),
            )
            .first()
        )

        if not landlord_property:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Landlord is outside your district scope",
            )

        return

    actor_landlord_id = get_actor_landlord_id(db, user)

    if actor_landlord_id != landlord_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Resource is outside your landlord scope",
        )


def get_property_in_scope(db: Session, user: User, property_id: uuid.UUID) -> Property:
    prop = db.get(Property, property_id)

    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    if is_national_admin(user):
        return prop

    if is_district_admin(user):
        assert_district_access(db, user, prop.district_id)
        return prop

    assert_landlord_access(db, user, prop.landlord_id)
    return prop


def get_room_in_scope(db: Session, user: User, room_id: uuid.UUID) -> Room:
    room = db.get(Room, room_id)

    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )

    if is_national_admin(user):
        return room

    if is_district_admin(user):
        prop = db.get(Property, room.property_id)

        if not prop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Room property not found",
            )

        assert_district_access(db, user, prop.district_id)
        return room

    assert_landlord_access(db, user, room.landlord_id)
    return room


def get_tenant_in_scope(db: Session, user: User, tenant_id: uuid.UUID) -> Tenant:
    tenant = db.get(Tenant, tenant_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    if user.role == UserRole.tenant and tenant.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant can only access own data",
        )

    if is_national_admin(user):
        return tenant

    if is_district_admin(user):
        tenant_property = (
            db.query(Property)
            .filter(Property.landlord_id == tenant.landlord_id)
            .first()
        )

        if not tenant_property:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant landlord property not found",
            )

        assert_district_access(db, user, tenant_property.district_id)
        return tenant

    assert_landlord_access(db, user, tenant.landlord_id)
    return tenant
