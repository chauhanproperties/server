# Chauhan Properties server

FastAPI + PostgreSQL API. The six-table schema follows the parent project's `database_tables.txt`.

## Local setup

Use Python 3.11 or newer. From this `server` directory:

```powershell
python -m venv --without-pip .venv
python -m pip --python .venv install -r requirements.txt
```

Keep credentials in `.env` (never commit it). Copy `.env.example` only when creating a new environment. Configure `ADMIN_EMAIL` and a unique `ADMIN_PASSWORD` of at least 16 characters. The password is checked by the API and is never included in the frontend. Use a different password for each environment.

Apply the initial schema migration:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Run the local API on port 5000:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 5000
```

Open `http://localhost:5000/health` and `http://localhost:5000/docs`. The admin panel is served separately on port 8000 from the parent directory:

```powershell
python -m http.server 8000 --bind 127.0.0.1 --directory ..\admin
```

Admin login uses `ADMIN_EMAIL` plus the server-only `ADMIN_PASSWORD`; failed login attempts are rate limited. `DEBUG=true` is for local use only and is rejected unless `ENVIRONMENT=local` or `development`. To send query replies by email, configure `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`, and `GMAIL_SENDER` for a Google OAuth client with the Gmail API `gmail.send` scope. Email is sent over Gmail API HTTPS, not SMTP. Production startup requires `ENVIRONMENT=production`, `DEBUG=false`, explicit allowed origins, a strong admin password, and Cloudinary credentials. Gmail settings are optional until email replies are enabled.

Interactive API documentation (`/docs`, `/redoc`, `/openapi.json`) is enabled locally and in development. It is disabled by default when `ENVIRONMENT=production`; set `ENABLE_DOCS=true` only temporarily when you need to test it on Render.

## Tests

Install development dependencies with `python -m pip --python .venv install -r requirements-dev.txt`. Unit tests that do not touch the database run without database configuration. Database integration tests use `TEST_DATABASE_URL` for a separate test database, such as a dedicated Neon branch, and refuse to run if it matches `DATABASE_URL`.

```powershell
pytest
ruff check .
```

The customer website is implemented in `../user` and runs on port 8001; see `../user/README.md` for details.

## Database changes

Create a new Alembic revision for schema changes, review it, then run `alembic upgrade head`. Do not recreate or drop tables to make a schema change.

## Hosting

For Render, set the root directory to `server`, install from `requirements.txt`, and use this exact start command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"
```

The forwarded IP setting is safe only when Render's proxy is the only way into the service. It lets the API rate-limit the real visitor address instead of treating every visitor as the same proxy. Configure environment variables in Render; do not upload `.env`. Set `DEBUG=false` and restrict `ALLOWED_ORIGINS` to the deployed frontends.
