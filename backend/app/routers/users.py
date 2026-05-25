import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.audit import log_action
from app.auth import authenticate_user, create_access_token, get_password_hash, verify_password
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.identity import next_identifier
from app.models import AuditAction, PasswordResetToken, TwoFactorChallenge, User, UserRole
from app.notification_channels import send_email, send_password_reset, send_sms, send_whatsapp
from app.schemas import AdminPasswordReset, PasswordChange, PasswordResetConfirm, PasswordResetRequest, Token, TwoFactorResendRequest, TwoFactorSetupRequest, TwoFactorVerifyRequest, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


def two_factor_required(user: User) -> bool:
    return user.role == UserRole.admin or user.two_factor_required or user.two_factor_enabled


def send_two_factor_code(user: User, otp: str, channel: str) -> None:
    message = f"Your LineLink security code is {otp}. It expires in 5 minutes."
    if channel == "whatsapp" and user.phone:
        send_whatsapp(user.phone, message)
    elif channel == "sms" and user.phone:
        send_sms(user.phone, message)
    else:
        send_email(user.email, "LineLink security code", message)


def create_two_factor_challenge(db: Session, user: User) -> tuple[TwoFactorChallenge, str]:
    otp = f"{secrets.randbelow(1_000_000):06d}"
    channel = user.preferred_2fa_channel or "email"
    challenge = TwoFactorChallenge(
        user_id=user.id,
        channel=channel,
        otp_hash=get_password_hash(otp),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        status="pending",
    )
    db.add(challenge)
    db.flush()
    send_two_factor_code(user, otp, channel)
    return challenge, otp


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
    if two_factor_required(user):
        challenge, otp = create_two_factor_challenge(db, user)
        log_action(db, AuditAction.login_success, actor=user, entity_type="TwoFactorChallenge", entity_id=challenge.id, metadata={"stage": "password_verified_2fa_required"})
        db.commit()
        response = Token(requires_2fa=True, challenge_id=challenge.id, channel=challenge.channel)
        if settings.app_env.strip().lower() in {"local", "development", "dev", "staging"}:
            response.demo_otp = otp
        return response
    log_action(db, AuditAction.login_success, actor=user, entity_type="User", entity_id=user.id)
    db.commit()
    return Token(access_token=create_access_token(str(user.id), {"role": user.role.value}))


@router.post("/2fa/verify", response_model=Token)
def verify_two_factor(payload: TwoFactorVerifyRequest, db: Session = Depends(get_db)):
    challenge = db.get(TwoFactorChallenge, payload.challenge_id)
    now = datetime.now(timezone.utc)
    if not challenge or challenge.status != "pending" or challenge.consumed_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Security code is invalid")
    expires_at = challenge.expires_at if challenge.expires_at.tzinfo else challenge.expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        challenge.status = "expired"
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Security code has expired")
    if challenge.attempts >= 5:
        challenge.status = "locked"
        db.commit()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many security code attempts")
    challenge.attempts += 1
    if not verify_password(payload.otp, challenge.otp_hash):
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Security code is incorrect")
    user = db.get(User, challenge.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or missing user")
    challenge.status = "consumed"
    challenge.consumed_at = now
    log_action(db, AuditAction.login_success, actor=user, entity_type="TwoFactorChallenge", entity_id=challenge.id, metadata={"stage": "2fa_verified"})
    db.commit()
    return Token(access_token=create_access_token(str(user.id), {"role": user.role.value}))


@router.post("/2fa/resend", response_model=Token)
def resend_two_factor(payload: TwoFactorResendRequest, db: Session = Depends(get_db)):
    old = db.get(TwoFactorChallenge, payload.challenge_id)
    if not old:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Security challenge not found")
    user = db.get(User, old.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or missing user")
    old.status = "revoked"
    challenge, otp = create_two_factor_challenge(db, user)
    db.commit()
    response = Token(requires_2fa=True, challenge_id=challenge.id, channel=challenge.channel)
    if settings.app_env.strip().lower() in {"local", "development", "dev", "staging"}:
        response.demo_otp = otp
    return response


@router.post("/2fa/setup", response_model=UserRead)
def setup_two_factor(payload: TwoFactorSetupRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.preferred_2fa_channel = payload.channel
    user.two_factor_enabled = payload.enabled
    if user.role == UserRole.admin:
        user.two_factor_required = True
    db.commit()
    db.refresh(user)
    return user


@router.post("/2fa/disable", response_model=UserRead)
def disable_two_factor(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == UserRole.admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin two-factor authentication is required")
    user.two_factor_enabled = False
    user.two_factor_required = False
    db.commit()
    db.refresh(user)
    return user


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
    response = {"detail": "If the account exists, a reset link or code will be sent."}
    if settings.app_env.strip().lower() in {"local", "development", "dev", "staging"}:
        response["reset_token_demo"] = token
    return response


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


@router.post("/admin/reset-user-password", response_model=UserRead)
def admin_reset_user_password(
    payload: AdminPasswordReset,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.admin)),
):
    identifier = payload.identifier.strip()
    user = db.query(User).filter((User.username == identifier) | (User.email == identifier)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account was not found")
    user.hashed_password = get_password_hash(payload.new_password)
    user.must_change_password = payload.must_change_password
    log_action(db, AuditAction.update_tenant, actor=admin, entity_type="User", entity_id=user.id, metadata={"identifier": identifier, "action": "admin_password_reset"})
    db.commit()
    db.refresh(user)
    return user
