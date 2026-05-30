from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_roles
from app.models import User, UserRole
from app.national_risk_logic import (
    calculate_high_risk_districts,
    calculate_national_collection_health,
    calculate_national_overdue_exposure,
    calculate_national_risk_distribution,
    generate_national_risk_summary,
)

router = APIRouter(prefix="/national-risk", tags=["national-risk"])


@router.get("/summary")
def national_risk_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.national_admin)),
):
    return generate_national_risk_summary(db)


@router.get("/distribution")
def national_risk_distribution(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.national_admin)),
):
    return calculate_national_risk_distribution(db)


@router.get("/high-risk-districts")
def national_high_risk_districts(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.national_admin)),
):
    return calculate_high_risk_districts(db)


@router.get("/collection-health")
def national_collection_health(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.national_admin)),
):
    return calculate_national_collection_health(db)


@router.get("/overdue-exposure")
def national_overdue_exposure(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.national_admin)),
):
    return calculate_national_overdue_exposure(db)
