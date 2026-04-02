from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database import Base, engine
from app.routers import auth, dashboard, transactions, users

# Create all tables on startup (Alembic handles migrations in production)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="""
## Finance Dashboard Backend

A role-based financial records management system built with FastAPI.

### Roles
| Role     | Permissions                                              |
|----------|----------------------------------------------------------|
| viewer   | View transactions, view dashboard summary                |
| analyst  | All viewer permissions + access to insights              |
| admin    | Full access: manage users, create/update/delete records  |

### Quick Start
1. Use `POST /auth/login` with seeded credentials to get a token
2. Click **Authorize** (top right) and paste: `<your_token>`
3. Explore the endpoints

### Seeded Test Users
| Email                  | Password  | Role     |
|------------------------|-----------|----------|
| admin@finance.com      | admin123  | admin    |
| analyst@finance.com    | analyst123| analyst  |
| viewer@finance.com     | viewer123 | viewer   |
""",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(transactions.router)
app.include_router(dashboard.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "app": settings.APP_NAME,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
