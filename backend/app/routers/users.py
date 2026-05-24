import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.audit import log_action
from app.auth import authenticate_user, create_access_token, get_password_hash, verify_password
from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.identity import next_identifier
from app.models import AuditAction, PasswordResetToken, User, UserRole
from app.notification_channels import send_password_reset
from app.schemas import PasswordChange, PasswordResetConfirm, PasswordResetRequest, Token, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead)
def register_user(payload: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.admin))):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
    user = User(
        email=str(payload.email),
        username=next_identifier(db, payload.role),
        phone=payload.phone,
        full_name=payload.full_name,
        role=payload.role,
        hashed_password=get_password_hash(payload.password),
        must_change_password=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        log_action(db, AuditAction.login_failure, entity_type="User", metadata={"identifier": form_data.username})
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    log_action(db, AuditAction.login_success, actor=user, entity_type="User", entity_id=user.id)
    db.commit()
    return Token(access_token=create_access_token(str(user.id), {"role": user.role.value}))


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    return UserRead.model_validate(current_user)


@router.post("/forgot-password")
def forgot_password(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    identifier = payload.identifier.strip()
    user = db.query(User).filter((User.username == identifier) | (User.email == identifier)).first()
    if not user:
        return {"detail": "If the account exists, a reset link or code will be sent."}
    token = secrets.token_urlsafe(32)
    reset = PasswordResetToken(
        user_id=user.id,
        token=token,
        channel=payload.channel,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(reset)
    send_password_reset(user, token, payload.channel)
    db.commit()
    return {"detail": "If the account exists, a reset link or code will be sent.", "reset_token_demo": token}


@router.post("/reset-password")
def reset_password(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    reset = db.query(PasswordResetToken).filter(PasswordResetToken.token == payload.token).first()
    now = datetime.now(timezone.utc)
    if not reset or reset.used_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token is invalid")
    expires_at = reset.expires_at if reset.expires_at.tzinfo else reset.expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token has expired")
    user = db.get(User, reset.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token is invalid")
    user.hashed_password = get_password_hash(payload.new_password)
    user.must_change_password = False
    reset.used_at = now
    db.commit()
    return {"detail": "Password reset complete"}


@router.post("/change-password")
def change_password(payload: PasswordChange, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    user.hashed_password = get_password_hash(payload.new_password)
    user.must_change_password = False
    db.commit()
    return {"detail": "Password changed"}
