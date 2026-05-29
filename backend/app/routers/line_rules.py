import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_actor_landlord_id, get_current_user, require_roles
from app.models import (
    LineRule,
    RuleAcknowledgement,
    RuleVisibility,
    Tenant,
    User,
    UserRole,
)
from app.ownership import get_tenant_in_scope, scoped_query
from app.schemas import LineRuleCreate, LineRuleRead

router = APIRouter(prefix="/line-rules", tags=["line rules"])


def actor_landlord_id(
    db: Session,
    user: User,
) -> uuid.UUID:
    landlord_id = get_actor_landlord_id(db, user)

    if not landlord_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No landlord scope",
        )

    return landlord_id


def rule_in_scope(
    db: Session,
    user: User,
    rule_id: uuid.UUID,
) -> LineRule:
    rule = db.get(LineRule, rule_id)

    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )

    if user.role == UserRole.tenant:
        tenant = db.query(Tenant).filter(Tenant.user_id == user.id).first()

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant profile not found",
            )

        if rule.landlord_id != tenant.landlord_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rule not found",
            )

        if rule.visibility == RuleVisibility.private and rule.tenant_id != tenant.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rule not found",
            )

        return rule

    scoped_rule = (
        scoped_query(db, user, LineRule)
        .filter(LineRule.id == rule.id)
        .first()
    )

    if not scoped_rule:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Rule is outside your scope",
        )

    return rule


@router.post("", response_model=LineRuleRead)
def create_rule(
    payload: LineRuleCreate,
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
    landlord_id = actor_landlord_id(db, user)

    if payload.tenant_id:
        get_tenant_in_scope(db, user, payload.tenant_id)

    rule = LineRule(
        landlord_id=landlord_id,
        **payload.model_dump(),
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)

    return rule


@router.get("", response_model=list[LineRuleRead])
def list_rules(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == UserRole.tenant:
        tenant = db.query(Tenant).filter(Tenant.user_id == user.id).first()

        if not tenant:
            return []

        return (
            db.query(LineRule)
            .filter(
                LineRule.landlord_id == tenant.landlord_id,
                (
                    (LineRule.visibility == RuleVisibility.public)
                    | (LineRule.tenant_id == tenant.id)
                ),
            )
            .order_by(LineRule.created_at.desc())
            .all()
        )

    return (
        scoped_query(db, user, LineRule)
        .order_by(LineRule.created_at.desc())
        .all()
    )


@router.put("/{rule_id}", response_model=LineRuleRead)
def update_rule(
    rule_id: uuid.UUID,
    payload: LineRuleCreate,
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
    rule = rule_in_scope(db, user, rule_id)

    if payload.tenant_id:
        get_tenant_in_scope(db, user, payload.tenant_id)

    for key, value in payload.model_dump().items():
        setattr(rule, key, value)

    db.commit()
    db.refresh(rule)

    return rule


@router.post("/{rule_id}/acknowledge")
def acknowledge_rule(
    rule_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.tenant)),
):
    tenant = db.query(Tenant).filter(Tenant.user_id == user.id).first()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant profile not found",
        )

    rule = rule_in_scope(db, user, rule_id)

    existing = (
        db.query(RuleAcknowledgement)
        .filter(
            RuleAcknowledgement.rule_id == rule.id,
            RuleAcknowledgement.tenant_id == tenant.id,
        )
        .first()
    )

    if not existing:
        db.add(
            RuleAcknowledgement(
                rule_id=rule.id,
                tenant_id=tenant.id,
            )
        )
        db.commit()

    return {"detail": "Rule acknowledged"}


@router.delete("/{rule_id}")
def delete_rule(
    rule_id: uuid.UUID,
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
    rule = rule_in_scope(db, user, rule_id)

    db.delete(rule)
    db.commit()

    return {"detail": "Rule deleted"}
