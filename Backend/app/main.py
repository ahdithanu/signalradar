import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db import SessionLocal
from app.models import Account, Signal, AccountSource, RawEvent, User, Workspace, WorkspaceMember  # noqa: F401
from app.routes import health, accounts, signals, workspaces, admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Production safety checks ---
    if settings.is_production:
        errors = settings.validate_production_config()
        if errors:
            for err in errors:
                logger.critical("FATAL CONFIG ERROR: %s", err)
            logger.critical(
                "Refusing to start in production with invalid configuration. "
                "Fix the errors above and restart."
            )
            sys.exit(1)

    # --- Dev seeding (only in non-production) ---
    if not settings.is_production:
        from app.services.seed import seed_dev_context, seed_accounts, seed_account_sources

        db = SessionLocal()
        try:
            ctx_count = seed_dev_context(db)
            if ctx_count:
                logger.info("Seeded dev context (%d new rows).", ctx_count)

            inserted = seed_accounts(db)
            if inserted:
                logger.info("Seeded %d account(s).", inserted)
            else:
                logger.info("Seed accounts already present, skipping.")

            sources_inserted = seed_account_sources(db)
            if sources_inserted:
                logger.info("Seeded %d account source(s).", sources_inserted)
            else:
                logger.info("Seed account sources already present, skipping.")
        finally:
            db.close()
    else:
        logger.info("Production mode — skipping dev seed data.")

    yield


app = FastAPI(
    title="Signal Radar API",
    version="0.3.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id"],
)
app.include_router(health.router)
app.include_router(accounts.router)
app.include_router(signals.router)
app.include_router(workspaces.router)
app.include_router(admin.router)
