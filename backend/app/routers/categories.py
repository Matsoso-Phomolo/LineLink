import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_roles
from app.models import PropertyCategory, User, UserRole
from app.ownership import assert_landlord_access, landlord_scope_filter
from app.schemas import PropertyCategoryCreate, PropertyCategoryRead

router = APIRouter(prefix="/categories", tags=["property categories"])


@router.post("", response_model=PropertyCategoryRead)
def create_category(payload: PropertyCategoryCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.landlord, UserRole.caretaker))):
    landlord_id = user.landlord_profile.id if user.role == UserRole.landlord and user.landlord_profile else user.caretaker_profile.landlord_id
    category = PropertyCategory(landlord_id=landlord_id, **payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("", response_model=list[PropertyCategoryRead])
def list_categories(db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.admin, UserRole.landlord, UserRole.caretaker))):
    return landlord_scope_filter(db, user, PropertyCategory).order_by(PropertyCategory.name.asc()).all()


@router.put("/{category_id}", response_model=PropertyCategoryRead)
def update_category(category_id: uuid.UUID, payload: PropertyCategoryCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.landlord, UserRole.caretaker))):
    category = db.get(PropertyCategory, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    assert_landlord_access(db, user, category.landlord_id)
    category.name = payload.name
    category.description = payload.description
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}")
def delete_category(category_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require_roles(UserRole.landlord, UserRole.caretaker))):
    category = db.get(PropertyCategory, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    assert_landlord_access(db, user, category.landlord_id)
    db.delete(category)
    db.commit()
    return {"detail": "Category deleted"}
