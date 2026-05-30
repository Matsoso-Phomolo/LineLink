from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_roles
from app.models import User, UserRole
from app.portfolio_risk_logic import (
    calculate_high_risk_tenants,
    calculate_landlord_risk_distribution,
    calculate_overdue_clusters,
    calculate_portfolio_collection_health,
    generate_landlord_portfolio_risk_summary,
)

router = APIRouter(prefix="/portfolio-risk", tags=["portfolio-risk"])


def get_landlord_id_for_portfolio_risk(user: User):
    if user.role == UserRole.landlord and user.landlord_profile:
        return user.landlord_profile.id

    if user.role == UserRole.caretaker and user.caretaker_profile:
        return user.caretaker_profile.landlord_id

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Portfolio risk is available only for landlord/caretaker scoped users.",
    )


@router.get("/summary")
def portfolio_risk_summary(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.landlord, UserRole.caretaker)),
):
    landlord_id = get_landlord_id_for_portfolio_risk(user)
    return generate_landlord_portfolio_risk_summary(db, landlord_id)


@router.get("/distribution")
def portfolio_risk_distribution(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.landlord, UserRole.caretaker)),
):
    landlord_id = get_landlord_id_for_portfolio_risk(user)
    return calculate_landlord_risk_distribution(db, landlord_id)


@router.get("/high-risk-tenants")
def portfolio_high_risk_tenants(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.landlord, UserRole.caretaker)),
):
    landlord_id = get_landlord_id_for_portfolio_risk(user)
    return calculate_high_risk_tenants(db, landlord_id)


@router.get("/overdue-clusters")
def portfolio_overdue_clusters(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.landlord, UserRole.caretaker)),
):
    landlord_id = get_landlord_id_for_portfolio_risk(user)
    return calculate_overdue_clusters(db, landlord_id)


@router.get("/collection-health")
def portfolio_collection_health(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.landlord, UserRole.caretaker)),
):
    landlord_id = get_landlord_id_for_portfolio_risk(user)
    return calculate_portfolio_collection_health(db, landlord_id)
