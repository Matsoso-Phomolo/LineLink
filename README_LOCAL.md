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

## Demo Logins

After `python -m app.seed`:

- Admin: `admin@linelink.local` / `ChangeMe123!`
- Landlord: `landlord1@linelink.com` / `Password123!`
- Tenant: `tenant1@linelink.com` / `Password123!`

Demo credentials are for local testing only and are intentionally not shown on the public login screen.

## Troubleshooting

- Port busy on `8001`: run the backend on another port, for example `--port 8002`, and update `VITE_API_BASE_URL`.
- Port busy on `8000` or `8002`: check running processes with `netstat -ano | findstr :8001`.
- Frontend cannot reach backend: confirm `ALLOWED_ORIGINS` includes the frontend origin.
- Bcrypt/passlib warning: this project pins `bcrypt==4.0.1` to avoid common passlib compatibility issues.
- Missing tables: run `alembic upgrade head` from the `backend` directory.
