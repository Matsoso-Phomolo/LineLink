# LineLink Local Development

## Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Git

## Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `backend/.env` with your local database URL and a local secret key. Do not commit `.env`.

For local development, you may keep demo seeding enabled:

```env
APP_ENV=local
SEED_DEMO_DATA=true
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=replace-with-a-secure-password
ADMIN_FULL_NAME=LineLink Admin
```

## PostgreSQL Setup

Create a database named `linelink`, then set:

```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/linelink
```

## Migrations and Seed Data

```powershell
cd backend
alembic upgrade head
python -m app.seed
```

`python -m app.seed` is environment-aware:

- Local/default mode creates the demo admin, landlord, tenant, rooms, listings, rent due, payment submission, ticket, and notifications.
- `APP_ENV=production` with `SEED_DEMO_DATA=false` creates only the first admin from `ADMIN_EMAIL`, `ADMIN_PASSWORD`, and `ADMIN_FULL_NAME`.
- Demo seed data is for local/staging only.

## Run Backend

```powershell
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Swagger is available at `http://127.0.0.1:8001/docs`.

## Frontend Setup

```powershell
cd frontend
npm install
copy .env.example .env
```

For local backend access, set:

```env
VITE_API_BASE_URL=http://127.0.0.1:8001
```

Run the frontend dev server:

```powershell
npm run dev
```

Or build and let FastAPI serve the compiled frontend:

```powershell
cd frontend
npm run build
cd ..\backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Open `http://127.0.0.1:8001/`.

## Deployment Validation

Run this before deploying or after setting production environment variables:

```powershell
cd backend
python -m app.validate_deployment
```

After the backend is running, include a health URL:

```powershell
python -m app.validate_deployment --health-url http://127.0.0.1:8001/health
```

The validation checks app imports, required environment variables, database connection, Alembic migration state, CORS origins, frontend build presence, and `/health` if a URL is provided.

## Demo Logins

After `python -m app.seed`:

- Admin: `admin@linelink.local` / `ChangeMe123!`
- Landlord: `landlord1@linelink.com` / `Password123!`
- Tenant: `tenant1@linelink.com` / `Password123!`

Demo credentials are for local testing only and are intentionally not shown on the public login screen.

Never use `ChangeMe123!` in production.

## Render Backend Deployment

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Production environment example:

```env
APP_ENV=production
SEED_DEMO_DATA=false
ADMIN_EMAIL=your-admin-email
ADMIN_PASSWORD=your-secure-password
ADMIN_FULL_NAME=LineLink Admin
DATABASE_URL=Render PostgreSQL URL
SECRET_KEY=secure-random-secret
ALLOWED_ORIGINS=https://your-vercel-domain.vercel.app
PUBLIC_BASE_URL=https://your-render-backend.onrender.com
```

Security notes:

- Never expose `.env`.
- Never use `ChangeMe123!` in production.
- Rotate `SECRET_KEY` before production.
- Keep `SEED_DEMO_DATA=false` in production.
- Demo seed is only for local/staging.

## Vercel Frontend Deployment

Set the frontend environment variable:

```env
VITE_API_BASE_URL=https://your-render-backend.onrender.com
```

Use:

- Framework preset: Vite
- Build command: `npm run build`
- Output directory: `dist`

If deploying from the repository root, use the root `vercel.json`.

## Post-Deployment Tests

1. Visit `https://your-render-backend.onrender.com/health`.
2. Open `https://your-render-backend.onrender.com/docs`.
3. Confirm CORS by opening the Vercel frontend and loading public listings.
4. Log in with the production admin created from `ADMIN_EMAIL`.
5. Confirm no demo landlord/tenant/listings exist when `SEED_DEMO_DATA=false`.
6. Create a landlord/property/room/listing, submit a public application, then approve and assign it.

## Troubleshooting

- Port busy on `8001`: run the backend on another port, for example `--port 8002`, and update `VITE_API_BASE_URL`.
- Port busy on `8000` or `8002`: check running processes with `netstat -ano | findstr :8001`.
- Frontend cannot reach backend: confirm `ALLOWED_ORIGINS` includes the frontend origin.
- Bcrypt/passlib warning: this project pins `bcrypt==4.0.1` to avoid common passlib compatibility issues.
- Missing tables: run `alembic upgrade head` from the `backend` directory.
