from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import (
    applications,
    audit_logs,
    caretakers,
    categories,
    complaints,
    dashboard,
    district_areas,
    districts,
    inspections,
    landlords,
    leases,
    line_rules,
    listings,
    messaging,
    national_admin,
    notifications,
    occupancies,
    payment_submissions,
    payments,
    properties,
    public_listings,
    reminders,
    rent_dues,
    rooms,
    subscriptions,
    support,
    tenant_accounts,
    tenant_portal,
    tenants,
    transfers,
    uploads,
    users,
)

app = FastAPI(
    title="LineLink API",
    version="0.1.0",
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "LineLink API",
    }


# =========================================================
# ROUTERS
# =========================================================

app.include_router(users.router)
app.include_router(national_admin.router)
app.include_router(landlords.router)
app.include_router(caretakers.router)
app.include_router(categories.router)
app.include_router(districts.router)
app.include_router(district_areas.router)
app.include_router(properties.router)
app.include_router(rooms.router)
app.include_router(tenants.router)
app.include_router(occupancies.router)
app.include_router(rent_dues.router)
app.include_router(reminders.router)
app.include_router(payments.router)
app.include_router(payment_submissions.router)
app.include_router(transfers.router)
app.include_router(listings.router)
app.include_router(public_listings.router)
app.include_router(public_listings.form_router)
app.include_router(tenant_accounts.router)
app.include_router(tenant_portal.router)
app.include_router(support.router)
app.include_router(uploads.router)
app.include_router(notifications.router)
app.include_router(audit_logs.router)
app.include_router(applications.router)
app.include_router(line_rules.router)
app.include_router(complaints.router)
app.include_router(leases.router)
app.include_router(messaging.router)
app.include_router(inspections.router)
app.include_router(subscriptions.router)
app.include_router(dashboard.router)


# =========================================================
# FRONTEND STATIC FILES
# =========================================================

if (FRONTEND_DIST / "assets").exists():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="frontend-assets",
    )


@app.get("/", include_in_schema=False)
def serve_frontend() -> FileResponse:
    index_path = FRONTEND_DIST / "index.html"

    if index_path.exists():
        return FileResponse(index_path)

    return FileResponse(PROJECT_ROOT / "frontend" / "index.html")
