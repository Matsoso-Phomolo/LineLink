from sqlalchemy.orm import Session

from app.models import Landlord, Tenant, User, UserRole


ROLE_PREFIXES = {
    UserRole.national_admin: "RL-NAT",
    UserRole.district_admin: "RL-DADM",
    UserRole.landlord: "RL-LND",
    UserRole.caretaker: "RL-CRT",
    UserRole.tenant: "RL-TNT",
}


def next_identifier(db: Session, role: UserRole) -> str:
    prefix = ROLE_PREFIXES[role]
    sequence = db.query(User).filter(User.username.like(f"{prefix}-%")).count() + 1

    while True:
        identifier = f"{prefix}-{sequence:06d}"

        if not db.query(User).filter(User.username == identifier).first():
            return identifier

        sequence += 1


def first_name_password(full_name: str) -> str:
    first = (full_name.strip().split() or ["tenant"])[0].lower()
    return f"{first}123"


def first_name_username(full_name: str) -> str:
    return (full_name.strip().split() or ["user"])[0].lower()


def sync_landlord_username(db: Session, landlord: Landlord) -> None:
    if landlord.user and landlord.system_landlord_number:
        landlord.user.username = landlord.system_landlord_number


def sync_tenant_username(db: Session, tenant: Tenant) -> None:
    if tenant.user and not tenant.user.username:
        tenant.user.username = next_identifier(db, UserRole.tenant)
