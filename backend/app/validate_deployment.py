import argparse
import urllib.request
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from app.config import settings
from app.database import Base


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist" / "index.html"


def ok(message: str) -> None:
    print(f"[ok] {message}")


def warn(message: str) -> None:
    print(f"[warn] {message}")


def fail(message: str, failures: list[str]) -> None:
    print(f"[fail] {message}")
    failures.append(message)


def check_required_env(failures: list[str]) -> None:
    required = {
        "DATABASE_URL": settings.database_url,
        "SECRET_KEY": settings.secret_key,
        "ALLOWED_ORIGINS": settings.allowed_origins,
        "CORS_ORIGINS": settings.cors_origins,
        "PUBLIC_BASE_URL": settings.public_base_url,
    }
    if settings.app_env.strip().lower() == "production":
        required.update({
            "APP_ENV": settings.app_env,
            "SEED_DEMO_DATA": str(settings.seed_demo_data),
            "ADMIN_EMAIL": settings.admin_email,
            "ADMIN_PASSWORD": settings.admin_password,
            "ADMIN_FULL_NAME": settings.admin_full_name,
        })
    missing = [key for key, value in required.items() if value is None or str(value).strip() == ""]
    if missing:
        fail(f"Missing required environment variables: {', '.join(missing)}", failures)
    else:
        ok("Required environment variables are present")
    if settings.secret_key == "change-me-in-production":
        fail("SECRET_KEY is still the placeholder value", failures)
    if settings.app_env.strip().lower() == "production" and settings.seed_demo_data:
        warn("SEED_DEMO_DATA=true in production; use only for intentional staging-style deployments")
    mopay_required = {
        "MOPAY_BASE_URL": settings.mopay_base_url,
        "MOPAY_API_KEY": settings.mopay_api_key,
        "MOPAY_MERCHANT_ID": settings.mopay_merchant_id,
        "MOPAY_WEBHOOK_SECRET": settings.mopay_webhook_secret,
        "MOPAY_CALLBACK_URL": settings.mopay_callback_url,
        "MOPAY_RETURN_URL": settings.mopay_return_url,
    }
    missing_mopay = [key for key, value in mopay_required.items() if not value]
    if missing_mopay:
        warn("MoPay is not fully configured yet: " + ", ".join(missing_mopay))
    else:
        ok("MoPay payment environment variables are configured")


def check_app_import(failures: list[str]) -> None:
    try:
        from app.main import app
    except Exception as exc:
        fail(f"App import failed: {exc}", failures)
        return
    ok(f"App imports successfully: {app.title}")


def check_database(failures: list[str]) -> None:
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as connection:
            connection.execute(text("select 1"))
        ok("Database connection works")
    except Exception as exc:
        fail(f"Database connection failed: {exc}", failures)


def check_schema_conflicts(failures: list[str]) -> None:
    try:
        engine = create_engine(settings.database_url)
        schema = "public" if engine.dialect.name == "postgresql" else None
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names(schema=schema))
        if not existing_tables:
            ok("Database schema has no existing tables")
            return

        rentalink_tables = set(Base.metadata.tables.keys())
        allowed_tables = rentalink_tables | {"alembic_version"}
        non_rentalink_tables = sorted(existing_tables - allowed_tables)
        if non_rentalink_tables:
            fail(
                "Database contains non-Rentalink tables. Use a clean database or a separate schema: "
                + ", ".join(non_rentalink_tables),
                failures,
            )
            return

        if "alembic_version" not in existing_tables and existing_tables.intersection(rentalink_tables):
            fail(
                "Rentalink tables exist but alembic_version is missing. This looks like a partial/manual schema; "
                "use a clean database or reset only if the data is disposable.",
                failures,
            )
            return

        ok("Existing database tables look compatible with Rentalink")
    except Exception as exc:
        fail(f"Schema conflict check failed: {exc}", failures)


def check_migrations(failures: list[str]) -> None:
    try:
        alembic_cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
        script = ScriptDirectory.from_config(alembic_cfg)
        engine = create_engine(settings.database_url)
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            current_revision = context.get_current_revision()
        head_revision = script.get_current_head()
        if current_revision != head_revision:
            fail(f"Database migration is not current: current={current_revision}, head={head_revision}", failures)
            return
        ok(f"Database migrations are current: {current_revision}")
    except Exception as exc:
        fail(f"Migration check failed: {exc}", failures)


def check_cors(failures: list[str]) -> None:
    origins = settings.allowed_origin_list
    if not origins:
        fail("ALLOWED_ORIGINS has no configured origins", failures)
        return
    ok(f"CORS origins configured: {', '.join(origins)}")
    if settings.app_env.strip().lower() == "production" and any("localhost" in origin or "127.0.0.1" in origin for origin in origins):
        warn("Production ALLOWED_ORIGINS includes localhost; remove it before public launch")


def check_frontend_build() -> None:
    if (REPO_ROOT / "frontend").exists():
        if FRONTEND_DIST.exists():
            ok("Frontend build exists for backend static serving")
        else:
            warn("Frontend build not found at frontend/dist/index.html; Vercel deployment is fine, but backend static serving will use frontend/index.html")


def check_health_url(health_url: str | None, failures: list[str]) -> None:
    if not health_url:
        warn("Skipping /health check because no --health-url was provided")
        return
    try:
        with urllib.request.urlopen(health_url, timeout=10) as response:
            body = response.read().decode("utf-8")
        if response.status != 200:
            fail(f"Health check returned HTTP {response.status}", failures)
            return
        ok(f"Health check passed at {health_url}: {body}")
    except Exception as exc:
        fail(f"Health check failed at {health_url}: {exc}", failures)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Rentalink deployment readiness")
    parser.add_argument("--health-url", help="Optional deployed or local health URL, for example https://api.example.com/health")
    args = parser.parse_args()

    failures: list[str] = []
    print(f"Rentalink deployment validation ({settings.app_env})")
    check_required_env(failures)
    check_app_import(failures)
    check_database(failures)
    check_schema_conflicts(failures)
    check_migrations(failures)
    check_cors(failures)
    check_frontend_build()
    check_health_url(args.health_url, failures)

    if failures:
        print("")
        print(f"Validation failed with {len(failures)} issue(s).")
        return 1
    print("")
    print("Deployment validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
