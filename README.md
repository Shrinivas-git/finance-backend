# Finance Dashboard Backend

## Live Demo

| | |
|---|---|
| API Base URL | https://web-production-88dfa.up.railway.app |
| Interactive Docs (Swagger) | https://web-production-88dfa.up.railway.app/docs |
| ReDoc | https://web-production-88dfa.up.railway.app/redoc |

> Use the test credentials below to log in via `/auth/login`, copy the token, click **Authorize** in `/docs`, and explore all endpoints.

---

A role-based financial records management API built with **FastAPI**, **SQLAlchemy**, and **SQLite** (swappable to PostgreSQL).

---

## Tech Stack

- Python 3.11+
- FastAPI 0.115
- SQLAlchemy 2.0 (ORM)
- SQLite (default) — change `DATABASE_URL` for PostgreSQL
- JWT authentication via `python-jose`
- Password hashing via `passlib[bcrypt]`
- Pydantic v2 for validation

---

## Setup

```bash
# 1. Install dependencies (use Python 3.11 — bcrypt wheel not yet available for 3.14)
py -3.11 -m pip install -r requirements.txt

# 2. Copy env file
cp .env.example .env

# 3. Seed the database with test users and sample transactions
py -3.11 seed.py

# 4. Start the server
py -3.11 -m uvicorn app.main:app --reload
```

API docs available at: http://localhost:8000/docs

---

## Test Credentials

| Email                   | Password    | Role     |
|-------------------------|-------------|----------|
| admin@finance.com       | admin123    | admin    |
| analyst@finance.com     | analyst123  | analyst  |
| viewer@finance.com      | viewer123   | viewer   |

---

## Role Permissions

| Action                          | Viewer | Analyst | Admin |
|---------------------------------|--------|---------|-------|
| Login / view own profile        | ✅     | ✅      | ✅    |
| List / view transactions        | ✅     | ✅      | ✅    |
| View dashboard summary          | ✅     | ✅      | ✅    |
| View analyst insights           | ❌     | ✅      | ✅    |
| Create / update / delete txns   | ❌     | ❌      | ✅    |
| Manage users (CRUD)             | ❌     | ❌      | ✅    |

---

## API Overview

### Auth
| Method | Endpoint      | Description                  |
|--------|---------------|------------------------------|
| POST   | /auth/login   | Login, returns JWT token     |
| GET    | /auth/me      | Get current user profile     |

### Transactions
| Method | Endpoint              | Access      | Description                        |
|--------|-----------------------|-------------|------------------------------------|
| POST   | /transactions/        | Admin       | Create a transaction               |
| GET    | /transactions/        | All roles   | List with filters + pagination     |
| GET    | /transactions/{id}    | All roles   | Get single transaction             |
| PATCH  | /transactions/{id}    | Admin       | Update a transaction               |
| DELETE | /transactions/{id}    | Admin       | Soft-delete a transaction          |

**Filters supported on GET /transactions/:**
- `type` — `income` or `expense`
- `category` — exact match (case-insensitive)
- `date_from` / `date_to` — YYYY-MM-DD
- `page` / `page_size` — pagination (default 1 / 20, max page_size 100)

### Users
| Method | Endpoint        | Access | Description         |
|--------|-----------------|--------|---------------------|
| POST   | /users/         | Admin  | Create a user       |
| GET    | /users/         | Admin  | List all users      |
| GET    | /users/{id}     | Admin  | Get user by ID      |
| PATCH  | /users/{id}     | Admin  | Update role/status  |
| DELETE | /users/{id}     | Admin  | Delete a user       |

### Dashboard
| Method | Endpoint              | Access           | Description                          |
|--------|-----------------------|------------------|--------------------------------------|
| GET    | /dashboard/summary    | All roles        | Totals, category breakdown, trends   |
| GET    | /dashboard/insights   | Analyst + Admin  | Averages, top categories, weekly trends |

---

## Data Model

### User
- `id`, `full_name`, `email` (unique), `hashed_password`
- `role` — `viewer` | `analyst` | `admin`
- `is_active` — can be deactivated without deletion
- `created_at`

### Transaction
- `id`, `amount` (positive float), `type` (`income` | `expense`)
- `category` (normalized to lowercase), `date`, `notes`
- `is_deleted` — soft delete flag (record preserved for audit)
- `created_at`, `updated_at` (auto-updated on every ORM write)
- `created_by` — FK to the admin user who created it

---

## Running Tests

```bash
py -3.11 -m pytest tests/ -v
```

Uses an in-memory SQLite database with `StaticPool` for thread-safe isolation. 19 tests covering auth, RBAC enforcement, input validation, soft delete, and analyst insights.

---

## Assumptions & Tradeoffs

- **SQLite by default** — zero setup for local dev. Swap to PostgreSQL by setting `DATABASE_URL=postgresql://...` in `.env`. The `connect_args` are applied conditionally so it won't break.
- **Soft delete only** — transactions are never hard-deleted to preserve audit trails. Soft-deleted records are excluded from all queries and dashboard aggregations.
- **Analyst insights computed in Python** — monthly/weekly aggregations are done in application code rather than SQL to stay DB-agnostic. Acceptable at this scale; for large datasets a materialized view or caching layer would be appropriate.
- **No Alembic migrations** — `Base.metadata.create_all()` runs on startup for simplicity. In a production setup, Alembic migrations would manage schema changes.
- **JWT expiry is 24 hours** — configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` in `.env`.
- **CORS allows all origins** — intentional for local development. Restrict `allow_origins` before deploying.
- **bcrypt pinned to 4.0.1** — `passlib 1.7.4` is incompatible with `bcrypt 4.x+` due to a version detection API change. Pinned to the last compatible release.
