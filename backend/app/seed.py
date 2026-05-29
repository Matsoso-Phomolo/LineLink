from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import get_password_hash
from app.config import settings
from app.database import SessionLocal
from app.models import (
    AllowedTenantType,
    District,
    Landlord,
    ListingVerificationStatus,
    ListingStatus,
    Notification,
    Occupancy,
    OccupancyStatus,
    PaymentMethod,
    PaymentSubmission,
    PaymentSubmissionStatus,
    Property,
    RentDue,
    RentDueStatus,
    Room,
    RoomListing,
    RoomStatus,
    RoomType,
    SubscriptionPlan,
    SupportTicket,
    Tenant,
    TenantType,
    TenantVerificationStatus,
    User,
    UserRole,
)
from app.lease_logic import generate_lease_for_occupancy

ADMIN_EMAIL = "admin@rentalink.local"
LANDLORD_EMAIL = "landlord1@rentalink.app"
TENANT_EMAIL = "tenant1@rentalink.app"
DEMO_ADMIN_PASSWORD = "ChangeMe123!"
DEMO_USER_PASSWORD = "Password123!"

LESOTHO_DISTRICTS = [
    ("Quthing", "quthing"),
    ("Mohale's Hoek", "mohales-hoek"),
    ("Mafeteng", "mafeteng"),
    ("Maseru", "maseru"),
    ("Berea", "berea"),
    ("Leribe", "leribe"),
    ("Botha-Bothe", "botha-bothe"),
    ("Thaba-Tseka", "thaba-tseka"),
    ("Mokhotlong", "mokhotlong"),
    ("Qacha's Nek", "qachas-nek"),
]


def current_month() -> date:
    today = date.today()
    return date(today.year, today.month, 1)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def get_or_create_user(
    db: Session,
    email: str,
    password: str,
    full_name: str,
    role: UserRole,
    phone: str | None = None,
) -> User:
    user = db.query(User).filter(User.email == email).first()

    if not user:
        user = User(
            email=email,
            full_name=full_name,
            role=role,
            hashed_password=get_password_hash(password),
            phone=phone,
        )
        db.add(user)
        db.flush()
    else:
        user.full_name = full_name
        user.role = role
        user.is_active = True
        user.must_change_password = False
        user.hashed_password = get_password_hash(password)

        if phone:
            user.phone = phone

    if not user.username:
        prefix = {
            UserRole.national_admin: "RL-NAT",
            UserRole.district_admin: "RL-DADM",
            UserRole.landlord: "RL-LND",
            UserRole.caretaker: "RL-CRT",
            UserRole.tenant: "RL-TNT",
        }[role]

        user.username = f"{prefix}-000001"

    return user


def bool_env(value: bool | str | None) -> bool:
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def is_production() -> bool:
    return settings.app_env.strip().lower() == "production"


def should_seed_demo_data() -> bool:
    return bool_env(settings.seed_demo_data)


def migrate_legacy_admin_roles(db: Session) -> None:
    db.execute(
        text(
            "UPDATE users SET role='national_admin' WHERE role='admin'"
        )
    )
    db.commit()


def seed_districts(db: Session) -> list[District]:
    districts: list[District] = []

    for name, slug in LESOTHO_DISTRICTS:
        district = db.query(District).filter(District.slug == slug).first()

        if not district:
            district = District(name=name, slug=slug)
            db.add(district)
            db.flush()

        district.name = name
        district.slug = slug

        if slug == "maseru":
            district.is_active = True
            district.rollout_stage = "roma_active"
            district.description = "Roma village active now"

            if not district.activated_at:
                district.activated_at = now_utc()
        else:
            district.is_active = False
            district.rollout_stage = "locked"
            district.description = "Future rollout"
            district.activated_at = None

        districts.append(district)

    return districts


def seed_admin(
    db: Session,
    *,
    email: str | None = None,
    password: str | None = None,
    full_name: str | None = None,
) -> User:
    admin_email = (
        email
        or settings.admin_email
        or (ADMIN_EMAIL if not is_production() else None)
    )
    admin_password = (
        password
        or settings.admin_password
        or (DEMO_ADMIN_PASSWORD if not is_production() else None)
    )
    admin_full_name = (
        full_name
        or settings.admin_full_name
        or "Phomolo Matsoso"
    )

    if not admin_email or not admin_password:
        raise RuntimeError(
            "ADMIN_EMAIL and ADMIN_PASSWORD are required when seeding the first national admin"
        )

    user = (
        db.query(User)
        .filter(
            (User.email == admin_email)
            | (User.username == "RL-NAT-000001")
        )
        .first()
    )

    if not user:
        user = User(
            username="RL-NAT-000001",
            email=admin_email,
            full_name=admin_full_name,
            role=UserRole.national_admin,
            hashed_password=get_password_hash(admin_password),
        )
        db.add(user)
        db.flush()
    else:
        user.email = admin_email
        user.full_name = admin_full_name
        user.username = "RL-NAT-000001"
        user.role = UserRole.national_admin
        user.is_active = True
        user.must_change_password = False
        user.two_factor_enabled = False
        user.two_factor_required = False
        user.preferred_2fa_channel = "email"
        user.hashed_password = get_password_hash(admin_password)

    return user


def seed_landlord(db: Session, user: User) -> Landlord:
    landlord = db.query(Landlord).filter(Landlord.user_id == user.id).first()

    if not landlord:
        landlord = Landlord(user_id=user.id)
        db.add(landlord)
        db.flush()

    landlord.business_name = "Matsoso Holdings"
    landlord.contact_phone = "+26658000000"
    landlord.email = LANDLORD_EMAIL
    landlord.address = "Roma, Lesotho"
    landlord.is_active = True

    if not landlord.system_landlord_number:
        landlord.system_landlord_number = "RL-LND-000001"

    user.username = landlord.system_landlord_number

    return landlord


def seed_property(db: Session, landlord: Landlord) -> Property:
    prop = (
        db.query(Property)
        .filter(
            Property.landlord_id == landlord.id,
            Property.name == "Roma Student Residence",
        )
        .first()
    )

    if not prop:
        prop = Property(
            landlord_id=landlord.id,
            name="Roma Student Residence",
            location_area="Roma",
        )
        db.add(prop)
        db.flush()

    prop.description = "Modern student accommodation near NUL"
    prop.address = "Roma, Lesotho"
    prop.location_area = "Roma"
    prop.country = "Lesotho"
    prop.distance_from_nul = "10 minutes walk"

    return prop


def seed_rooms(
    db: Session,
    landlord: Landlord,
    prop: Property,
) -> dict[str, Room]:
    room_specs = [
        ("A-101", RoomType.single, "medium", RoomStatus.vacant, Decimal("500"), Decimal("500")),
        ("A-102", RoomType.single, "medium", RoomStatus.vacant, Decimal("550"), Decimal("550")),
        ("A-103", RoomType.double, "large", RoomStatus.vacant, Decimal("800"), Decimal("800")),
        ("B-101", RoomType.single, "small", RoomStatus.occupied, Decimal("450"), Decimal("450")),
        ("B-102", RoomType.double, "large", RoomStatus.vacant, Decimal("850"), Decimal("850")),
    ]

    rooms: dict[str, Room] = {}

    for room_number, room_type, room_size, status, rent_price, deposit_amount in room_specs:
        room = (
            db.query(Room)
            .filter(
                Room.property_id == prop.id,
                Room.room_number == room_number,
            )
            .first()
        )

        if not room:
            room = Room(
                property_id=prop.id,
                landlord_id=landlord.id,
                room_number=room_number,
                status=status,
                room_type=room_type,
                room_size=room_size,
                rent_price=rent_price,
                deposit_amount=deposit_amount,
            )
            db.add(room)
            db.flush()

        room.landlord_id = landlord.id
        room.status = status
        room.room_type = room_type
        room.room_size = room_size
        room.rent_price = rent_price
        room.deposit_amount = deposit_amount

        rooms[room_number] = room

    return rooms


def seed_listings(
    db: Session,
    landlord: Landlord,
    prop: Property,
    rooms: dict[str, Room],
) -> dict[str, RoomListing]:
    listings: dict[str, RoomListing] = {}

    for room in rooms.values():
        listing = db.query(RoomListing).filter(RoomListing.room_id == room.id).first()

        if room.status != RoomStatus.vacant:
            if listing:
                listing.status = ListingStatus.rented
                listing.is_public = False
            continue

        if not listing:
            listing = RoomListing(
                landlord_id=landlord.id,
                property_id=prop.id,
                room_id=room.id,
                title=f"{room.room_number} {room.room_size} {room.room_type.value} room in Roma",
                description=f"Public listing for room {room.room_number} at Roma Student Residence.",
                rent_price=room.rent_price,
                deposit_amount=room.deposit_amount,
                room_type=room.room_type,
                room_size=room.room_size,
                location_area="Roma",
                allowed_tenant_type=AllowedTenantType.both,
                available_from=current_month(),
                distance_from_nul="10 minutes walk",
                contact_phone="+26658000000",
                water_available=True,
                electricity_available=True,
                security_features="Fence and lockable gate",
                house_rules="No excessive noise",
                status=ListingStatus.published,
                is_public=True,
                is_verified=True,
                verification_status=ListingVerificationStatus.verified,
            )
            db.add(listing)
            db.flush()

        listing.landlord_id = landlord.id
        listing.property_id = prop.id
        listing.title = f"{room.room_number} {room.room_size} {room.room_type.value} room in Roma"
        listing.description = f"Public listing for room {room.room_number} at Roma Student Residence."
        listing.rent_price = room.rent_price
        listing.deposit_amount = room.deposit_amount
        listing.room_type = room.room_type
        listing.room_size = room.room_size
        listing.location_area = "Roma"
        listing.allowed_tenant_type = AllowedTenantType.both
        listing.available_from = current_month()
        listing.distance_from_nul = "10 minutes walk"
        listing.contact_phone = "+26658000000"
        listing.water_available = True
        listing.electricity_available = True
        listing.security_features = "Fence and lockable gate"
        listing.house_rules = "No excessive noise"
        listing.status = ListingStatus.published
        listing.is_public = True
        listing.is_verified = True
        listing.verification_status = ListingVerificationStatus.verified
        listing.internet_included = True
        listing.furnished = room.room_number in {"A-103", "B-102"}
        listing.parking_available = False
        listing.pets_allowed = False

        listings[room.room_number] = listing

    return listings


def seed_tenant(
    db: Session,
    landlord: Landlord,
    user: User,
) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.user_id == user.id).first()

    if not tenant:
        tenant = Tenant(
            user_id=user.id,
            landlord_id=landlord.id,
            full_name="Test Tenant",
            phone="+26659000000",
            tenant_type=TenantType.student,
        )
        db.add(tenant)
        db.flush()

    tenant.landlord_id = landlord.id
    tenant.full_name = "Test Tenant"
    tenant.phone = "+26659000000"
    tenant.email = TENANT_EMAIL
    tenant.tenant_type = TenantType.student
    tenant.student_number = "20240001"
    tenant.institution = "National University of Lesotho"
    tenant.verification_status = TenantVerificationStatus.pending_verification

    if user:
        user.username = user.username or "RL-TNT-000001"
        user.must_change_password = False

    tenant.lease_start_date = current_month()
    tenant.monthly_rent = 450
    tenant.deposit_amount = 450
    tenant.deposit_paid = False
    tenant.outstanding_balance = 450

    return tenant


def seed_occupancy_and_rent(
    db: Session,
    landlord: Landlord,
    tenant: Tenant,
    room: Room,
) -> tuple[Occupancy, RentDue]:
    occupancy = (
        db.query(Occupancy)
        .filter(
            Occupancy.tenant_id == tenant.id,
            Occupancy.room_id == room.id,
            Occupancy.status == OccupancyStatus.active,
        )
        .first()
    )

    if not occupancy:
        occupancy = Occupancy(
            landlord_id=landlord.id,
            tenant_id=tenant.id,
            room_id=room.id,
            move_in_date=current_month(),
            monthly_rent=room.rent_price,
            deposit_amount=room.deposit_amount,
            billing_start_month=current_month(),
            status=OccupancyStatus.active,
        )
        db.add(occupancy)
        db.flush()

    occupancy.landlord_id = landlord.id
    occupancy.monthly_rent = room.rent_price
    occupancy.deposit_amount = room.deposit_amount
    occupancy.billing_start_month = current_month()
    occupancy.status = OccupancyStatus.active
    room.status = RoomStatus.occupied

    generate_lease_for_occupancy(db, occupancy)

    due = (
        db.query(RentDue)
        .filter(
            RentDue.occupancy_id == occupancy.id,
            RentDue.due_month == current_month(),
        )
        .first()
    )

    if not due:
        due = RentDue(
            landlord_id=landlord.id,
            tenant_id=tenant.id,
            occupancy_id=occupancy.id,
            due_month=current_month(),
            amount_due=room.rent_price,
            amount_paid=Decimal("0"),
            status=RentDueStatus.unpaid,
        )
        db.add(due)
        db.flush()

    due.landlord_id = landlord.id
    due.tenant_id = tenant.id
    due.amount_due = room.rent_price
    due.status = RentDueStatus.unpaid

    return occupancy, due


def seed_payment(
    db: Session,
    landlord: Landlord,
    tenant: Tenant,
    due: RentDue,
) -> PaymentSubmission:
    payment = (
        db.query(PaymentSubmission)
        .filter(
            PaymentSubmission.landlord_id == landlord.id,
            PaymentSubmission.transaction_reference == "MPESA-DEMO-001",
        )
        .first()
    )

    if not payment:
        payment = PaymentSubmission(
            landlord_id=landlord.id,
            tenant_id=tenant.id,
            rent_due_id=due.id,
            amount=Decimal("450"),
            method=PaymentMethod.mpesa,
            transaction_reference="MPESA-DEMO-001",
            status=PaymentSubmissionStatus.pending,
        )
        db.add(payment)
        db.flush()

    payment.tenant_id = tenant.id
    payment.rent_due_id = due.id
    payment.amount = Decimal("450")
    payment.method = PaymentMethod.mpesa
    payment.status = PaymentSubmissionStatus.pending

    return payment


def seed_support_ticket(
    db: Session,
    landlord: Landlord,
    tenant: Tenant,
) -> SupportTicket:
    ticket = (
        db.query(SupportTicket)
        .filter(
            SupportTicket.tenant_id == tenant.id,
            SupportTicket.title == "Broken door lock",
        )
        .first()
    )

    if not ticket:
        ticket = SupportTicket(
            landlord_id=landlord.id,
            tenant_id=tenant.id,
            title="Broken door lock",
            category="maintenance",
            description="My room door lock needs repair.",
        )
        db.add(ticket)
        db.flush()

    ticket.landlord_id = landlord.id
    ticket.category = "maintenance"
    ticket.priority = "high"
    ticket.description = "My room door lock needs repair."

    return ticket


def seed_notification(
    db: Session,
    user: User,
    title: str,
    body: str,
    category: str,
) -> Notification:
    notification = (
        db.query(Notification)
        .filter(
            Notification.user_id == user.id,
            Notification.title == title,
            Notification.category == category,
        )
        .first()
    )

    if not notification:
        notification = Notification(
            user_id=user.id,
            title=title,
            body=body,
            category=category,
            is_read=False,
        )
        db.add(notification)
        db.flush()
    else:
        notification.body = body
        notification.is_read = False

    return notification


def seed_subscription_plans(db: Session) -> None:
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "Starter").first()

    if not plan:
        plan = SubscriptionPlan(
            name="Starter",
            monthly_price=Decimal("99"),
            max_properties=2,
            max_rooms=20,
        )
        db.add(plan)
        db.flush()

    plan.features = "Room listings, tenant management, rent tracking, support tickets"
    plan.is_active = True


def seed_demo_data(db: Session) -> dict[str, object]:
    if is_production() and not should_seed_demo_data():
        raise RuntimeError(
            "Refusing to seed demo data in production when SEED_DEMO_DATA=false"
        )

    seed_districts(db)
    seed_admin(
        db,
        email=ADMIN_EMAIL,
        password=DEMO_ADMIN_PASSWORD,
        full_name="Phomolo Matsoso",
    )

    landlord_user = get_or_create_user(
        db,
        LANDLORD_EMAIL,
        DEMO_USER_PASSWORD,
        "Matsoso Holdings",
        UserRole.landlord,
        "+26658000000",
    )

    tenant_user = get_or_create_user(
        db,
        TENANT_EMAIL,
        DEMO_USER_PASSWORD,
        "Test Tenant",
        UserRole.tenant,
        "+26659000000",
    )

    landlord = seed_landlord(db, landlord_user)
    prop = seed_property(db, landlord)
    rooms = seed_rooms(db, landlord, prop)
    tenant = seed_tenant(db, landlord, tenant_user)
    occupancy, due = seed_occupancy_and_rent(db, landlord, tenant, rooms["B-101"])
    listings = seed_listings(db, landlord, prop, rooms)
    payment = seed_payment(db, landlord, tenant, due)

    seed_support_ticket(db, landlord, tenant)

    seed_notification(
        db,
        landlord_user,
        "New payment submission",
        "Test Tenant submitted MPESA-DEMO-001 for M450.",
        "payments",
    )

    seed_notification(
        db,
        tenant_user,
        "Rent due created",
        "Your current month rent due is M450.",
        "rent_dues",
    )

    seed_subscription_plans(db)

    return {
        "landlord": landlord,
        "property": prop,
        "rooms": rooms,
        "tenant": tenant,
        "occupancy": occupancy,
        "due": due,
        "listings": listings,
        "payment": payment,
    }


def seed() -> None:
    db = SessionLocal()

    try:
        migrate_legacy_admin_roles(db)

        seed_districts(db)

        demo_enabled = should_seed_demo_data() or not is_production()

        if demo_enabled:
            result = seed_demo_data(db)
            db.commit()

            print("Rentalink demo seed complete")
            print("")
            print("Demo logins")
            print(f"- national_admin: RL-NAT-000001 / {DEMO_ADMIN_PASSWORD}")
            print(f"- landlord: RL-LND-000001 / {DEMO_USER_PASSWORD}")
            print(f"- tenant: RL-TNT-000001 / {DEMO_USER_PASSWORD}")
            print("Legacy email login is still accepted for local compatibility.")
            print("")

            landlord = result["landlord"]
            prop = result["property"]
            tenant = result["tenant"]
            occupancy = result["occupancy"]
            due = result["due"]
            payment = result["payment"]
            rooms = result["rooms"]
            listings = result["listings"]

            print(f"landlord_id: {landlord.id}")
            print(f"property_id: {prop.id}")
            print("room IDs:")

            for room_number, room in rooms.items():
                print(f"- {room_number}: {room.id}")

            print("listing IDs:")

            for room_number, listing in listings.items():
                print(f"- {room_number}: {listing.id}")

            print(f"tenant_id: {tenant.id}")
            print(f"occupancy_id: {occupancy.id}")
            print(f"rent_due_id: {due.id}")
            print(f"payment_submission_id: {payment.id}")
        else:
            admin = seed_admin(db)
            db.commit()

            print("Rentalink production national admin setup complete")
            print(f"national_admin_email: {admin.email}")
            print(f"national_admin_id: {admin.id}")
            print("Demo data skipped because APP_ENV=production and SEED_DEMO_DATA=false")
    finally:
        db.close()


def seed_demo() -> None:
    seed()


if __name__ == "__main__":
    seed()
