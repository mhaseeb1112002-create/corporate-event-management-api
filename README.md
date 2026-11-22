# Corporate Event Management API

An asynchronous FastAPI application for managing Acme Corp events and employee registrations. Events are stored in PostgreSQL. Swagger UI is available at `/docs`.

## Requirements

- Python 3.10+ and PostgreSQL 14+
- A PostgreSQL database and a user with permission to create tables

## Setup

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create the PostgreSQL user and database using `psql` as a PostgreSQL administrator (replace the example password):

```sql
CREATE USER event_user WITH PASSWORD 'choose-a-strong-password';
CREATE DATABASE event_db OWNER event_user;
```

Set the database URL and a random JWT signing secret in your shell. URL-encode special characters in the password. **Do not commit credentials or a real `.env` file.**

```bash
export DATABASE_URL='postgresql+asyncpg://event_user:choose-a-strong-password@localhost:5432/event_db'
export JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
python create_user.py admin
uvicorn main:app --reload
```

On Windows PowerShell use `$env:DATABASE_URL = '...'` and `$env:JWT_SECRET = 'your-random-secret-of-at-least-32-characters'`. For non-demo use, keep the same secret securely across restarts, enforce HTTPS, use a secrets manager, and use migrations instead of `create_all`. The script prompts for a password of at least 12 characters. On startup the app creates missing tables; it does not migrate existing schemas.

## Try the API

Open `http://127.0.0.1:8000/docs`. Click **Authorize**, enter the username and password from `create_user.py`, and authorize. Swagger calls `/token` to obtain a 30-minute bearer token. Event creation, update, and deletion require a valid token. Event reads and registration routes are public for this assignment; **do not expose employee details publicly in production**. In a real internal service protect registrations as well and implement authorization and rate limits.

Use the sample request below to create an event:

```json
{"title":"Python Workshop","description":"Learn FastAPI","date":"2027-06-10","location":"Conference Room","max_capacity":2}
```

Registration example:

```json
{"employee_name":"Ali Khan","employee_email":"ali@example.com"}
```

| Method | Path | Purpose | Auth |
|---|---|---|---|
| POST | `/token` | Login (form username/password) | No |
| POST | `/events` | Create an event | Yes |
| GET | `/events` | List; optional `skip`, `limit`, `title`, `date` | No |
| GET | `/events/{event_id}` | Retrieve an event | No |
| PUT | `/events/{event_id}` | Replace all event fields | Yes |
| DELETE | `/events/{event_id}` | Delete event and registrations | Yes |
| POST | `/events/{event_id}/registrations` | Register employee | No |
| GET | `/events/{event_id}/registrations` | List registrations, with pagination | No |
| DELETE | `/registrations/{registration_id}` | Cancel registration | No |

Responses use 201 for creation, 204 for deletion, 404 for missing resources, 409 for duplicates/full capacity and 422 for invalid data. `PUT` refuses a capacity lower than the number of existing registrations. Email addresses are normalized to lowercase. For PostgreSQL, the registration service locks the event row before checking capacity; a database unique constraint also prevents duplicate registrations. Deleting an event also removes its registrations.

## Project structure

- `db.py`: async engine, sessions, and declarative base.
- `models.py`: event, registration, and login tables and constraints.
- `schemas.py`: Pydantic request and response validation.
- `services.py`: queries, transaction handling, and business rules.
- `main.py`: routes, dependency injection, and OpenAPI documentation.
- `auth.py`: password hashing and JWT verification.
- `create_user.py`: command-line account provisioning.
- `test_api.py`: automated tests. `DEMO_GUIDE.md` outlines a demonstration.

## Tests

```bash
python -m pytest -q
```

The pytest suite uses SQLite for isolated functional tests. A separate PostgreSQL integration check was run successfully against a temporary local PostgreSQL instance, including two simultaneous registrations for one seat: one returned 201 and the other 409. To repeat this optional check on a compatible Unix environment, install `pgserver` in the virtual environment and run:

```bash
python -m pip install pgserver
PYTHONPATH=. python postgres_integration.py
```

This script starts a temporary local test database using trust authentication on port 55472; run it only in a trusted local environment. It stops the database afterward. The pytest SQLite suite alone does not test PostgreSQL locking. Windows users should perform the equivalent integration checks against a separate PostgreSQL test database.

## Further limitations

This educational project has no migrations, token revocation, account-management UI, rate limiting, roles, or production deployment configuration. Public registration cancellation uses a numeric ID and is unsafe for a real deployment without authentication and authorization. Treat it as a learning project, not a production-ready service.
