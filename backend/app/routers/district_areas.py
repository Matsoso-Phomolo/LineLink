import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_optional_current_user, require_roles
from app.models import District, DistrictAdminAssignment, DistrictArea, DistrictVillage, User, UserRole
from app.schemas import (
    DistrictAreaCreate,
    DistrictAreaResponse,
    DistrictAreaUpdate,
    DistrictVillageCreate,
    DistrictVillageResponse,
    DistrictVillageUpdate,
)

router = APIRouter(prefix="/district-areas", tags=["district areas"])


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-")


def ensure_area_slug(db: Session, district: District, area_name: str) -> str:
    base_slug = f"{district.slug}-{slugify(area_name)}"
    slug = base_slug
    counter = 2

    while db.query(DistrictArea).filter(DistrictArea.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


def ensure_village_slug(db: Session, area: DistrictArea, village_name: str) -> str:
    base_slug = f"{area.slug}-{slugify(village_name)}"
    slug = base_slug
    counter = 2

    while db.query(DistrictVillage).filter(DistrictVillage.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


def is_national_admin(user: User) -> bool:
    return user.role == UserRole.national_admin


def is_district_admin(user: User) -> bool:
    return user.role == UserRole.district_admin


def user_can_manage_district(db: Session, user: User, district_id: uuid.UUID) -> bool:
    if is_national_admin(user):
        return True

    if not is_district_admin(user):
        return False

    return (
        db.query(DistrictAdminAssignment)
        .filter(
            DistrictAdminAssignment.user_id == user.id,
            DistrictAdminAssignment.district_id == district_id,
        )
        .first()
        is not None
    )


def assigned_district_id_for_area_create(
    db: Session,
    user: User,
    requested_district_id: uuid.UUID,
) -> uuid.UUID:
    if is_national_admin(user):
        return requested_district_id

    if not is_district_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    assignments = (
        db.query(DistrictAdminAssignment)
        .filter(
            DistrictAdminAssignment.user_id == user.id,
            DistrictAdminAssignment.is_active.is_(True),
        )
        .order_by(DistrictAdminAssignment.created_at.asc())
        .all()
    )

    if not assignments:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No district assignment found. Contact National Admin.",
        )

    assigned_ids = {assignment.district_id for assignment in assignments}
    if requested_district_id not in assigned_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add areas inside your assigned district",
        )

    return requested_district_id


def area_in_scope(db: Session, user: User, area_id: uuid.UUID) -> DistrictArea:
    area = db.get(DistrictArea, area_id)
    if not area:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found",
        )

    if not user_can_manage_district(db, user, area.district_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Area is outside your assigned district",
        )

    return area


@router.get("", response_model=list[DistrictAreaResponse])
def list_district_areas(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> list[DistrictArea]:
    if current_user and is_district_admin(current_user):
        return (
            db.query(DistrictArea)
            .join(DistrictAdminAssignment, DistrictAdminAssignment.district_id == DistrictArea.district_id)
            .filter(
                DistrictAdminAssignment.user_id == current_user.id,
                DistrictAdminAssignment.is_active.is_(True),
            )
            .order_by(DistrictArea.name.asc())
            .all()
        )

    return (
        db.query(DistrictArea)
        .order_by(DistrictArea.name.asc())
        .all()
    )


@router.get("/active", response_model=list[DistrictAreaResponse])
def list_active_district_areas(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> list[DistrictArea]:
    if current_user and is_district_admin(current_user):
        return (
            db.query(DistrictArea)
            .join(DistrictAdminAssignment, DistrictAdminAssignment.district_id == DistrictArea.district_id)
            .filter(
                DistrictAdminAssignment.user_id == current_user.id,
                DistrictAdminAssignment.is_active.is_(True),
                DistrictArea.is_active.is_(True),
            )
            .order_by(DistrictArea.name.asc())
            .all()
        )

    return (
        db.query(DistrictArea)
        .filter(DistrictArea.is_active.is_(True))
        .order_by(DistrictArea.name.asc())
        .all()
    )


@router.get("/district/{district_id}", response_model=list[DistrictAreaResponse])
def list_areas_for_district(
    district_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> list[DistrictArea]:
    if current_user and is_district_admin(current_user) and not user_can_manage_district(db, current_user, district_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="District is outside your assigned scope",
        )

    return (
        db.query(DistrictArea)
        .filter(DistrictArea.district_id == district_id)
        .order_by(DistrictArea.name.asc())
        .all()
    )


@router.get("/district/{district_id}/active", response_model=list[DistrictAreaResponse])
def list_active_areas_for_district(
    district_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> list[DistrictArea]:
    if current_user and is_district_admin(current_user) and not user_can_manage_district(db, current_user, district_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="District is outside your assigned scope",
        )

    return (
        db.query(DistrictArea)
        .filter(
            DistrictArea.district_id == district_id,
            DistrictArea.is_active.is_(True),
        )
        .order_by(DistrictArea.name.asc())
        .all()
    )


@router.get("/villages", response_model=list[DistrictVillageResponse])
def list_villages(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> list[DistrictVillage]:
    query = db.query(DistrictVillage).join(DistrictArea, DistrictArea.id == DistrictVillage.area_id)

    if current_user and is_district_admin(current_user):
        query = query.join(
            DistrictAdminAssignment,
            DistrictAdminAssignment.district_id == DistrictArea.district_id,
        ).filter(
            DistrictAdminAssignment.user_id == current_user.id,
            DistrictAdminAssignment.is_active.is_(True),
        )

    return query.order_by(DistrictVillage.name.asc()).all()


@router.get("/{area_id}/villages", response_model=list[DistrictVillageResponse])
def list_villages_for_area(
    area_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> list[DistrictVillage]:
    area = db.get(DistrictArea, area_id)
    if not area:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found",
        )

    if current_user and is_district_admin(current_user) and not user_can_manage_district(db, current_user, area.district_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Area is outside your assigned district",
        )

    return (
        db.query(DistrictVillage)
        .filter(DistrictVillage.area_id == area_id)
        .order_by(DistrictVillage.name.asc())
        .all()
    )


@router.post("/{area_id}/villages", response_model=DistrictVillageResponse, status_code=status.HTTP_201_CREATED)
def create_village(
    area_id: uuid.UUID,
    payload: DistrictVillageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.national_admin, UserRole.district_admin)),
) -> DistrictVillage:
    area = area_in_scope(db, current_user, area_id)

    existing = (
        db.query(DistrictVillage)
        .filter(
            DistrictVillage.area_id == area.id,
            DistrictVillage.name.ilike(payload.name.strip()),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Village already exists under this area",
        )

    village = DistrictVillage(
        area_id=area.id,
        name=payload.name.strip(),
        slug=ensure_village_slug(db, area, payload.name),
        description=payload.description,
        is_active=payload.is_active,
    )

    db.add(village)
    db.commit()
    db.refresh(village)

    return village


@router.patch("/villages/{village_id}", response_model=DistrictVillageResponse)
def update_village(
    village_id: uuid.UUID,
    payload: DistrictVillageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.national_admin, UserRole.district_admin)),
) -> DistrictVillage:
    village = db.get(DistrictVillage, village_id)
    if not village:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Village not found",
        )

    area_in_scope(db, current_user, village.area_id)
    update_data = payload.model_dump(exclude_unset=True)

    if "name" in update_data and update_data["name"]:
        village.name = update_data["name"].strip()

    if "description" in update_data:
        village.description = update_data["description"]

    if "is_active" in update_data:
        village.is_active = update_data["is_active"]

    db.add(village)
    db.commit()
    db.refresh(village)

    return village


@router.delete("/villages/{village_id}")
def delete_village(
    village_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.national_admin, UserRole.district_admin)),
) -> dict[str, str]:
    village = db.get(DistrictVillage, village_id)
    if not village:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Village not found",
        )

    area_in_scope(db, current_user, village.area_id)

    db.delete(village)
    db.commit()

    return {"detail": "Village deleted"}


@router.post("", response_model=DistrictAreaResponse, status_code=status.HTTP_201_CREATED)
def create_district_area(
    payload: DistrictAreaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.national_admin, UserRole.district_admin)),
) -> DistrictArea:
    district_id = assigned_district_id_for_area_create(db, current_user, payload.district_id)
    district = db.query(District).filter(District.id == district_id).first()

    if not district:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="District not found",
        )

    if not user_can_manage_district(db, current_user, district.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add areas inside your assigned district",
        )

    existing = (
        db.query(DistrictArea)
        .filter(
            DistrictArea.district_id == district.id,
            DistrictArea.name.ilike(payload.name.strip()),
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Area already exists in this district",
        )

    area = DistrictArea(
        district_id=district.id,
        name=payload.name.strip(),
        slug=ensure_area_slug(db, district, payload.name),
        description=payload.description,
        is_active=payload.is_active,
    )

    db.add(area)
    db.commit()
    db.refresh(area)

    return area


@router.patch("/{area_id}", response_model=DistrictAreaResponse)
def update_district_area(
    area_id: uuid.UUID,
    payload: DistrictAreaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.national_admin, UserRole.district_admin)),
) -> DistrictArea:
    area = db.query(DistrictArea).filter(DistrictArea.id == area_id).first()

    if not area:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found",
        )

    if not user_can_manage_district(db, current_user, area.district_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update areas inside your assigned district",
        )

    update_data = payload.model_dump(exclude_unset=True)

    if "name" in update_data and update_data["name"]:
        area.name = update_data["name"].strip()

    if "description" in update_data:
        area.description = update_data["description"]

    if "is_active" in update_data:
        area.is_active = update_data["is_active"]

    db.add(area)
    db.commit()
    db.refresh(area)

    return area


@router.delete("/{area_id}")
def delete_district_area(
    area_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.national_admin, UserRole.district_admin)),
) -> dict[str, str]:
    area = db.query(DistrictArea).filter(DistrictArea.id == area_id).first()

    if not area:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Area not found",
        )

    if not user_can_manage_district(db, current_user, area.district_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete areas inside your assigned district",
        )

    db.delete(area)
    db.commit()

    return {"detail": "Area deleted"}
