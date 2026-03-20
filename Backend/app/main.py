import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db import engine, SessionLocal, Base
from app.routes import health, accounts
from app.services.seed import seed_accounts
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Creating tables if they do not exist...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        inserted = seed_accounts(db)
        if inserted:
            logger.info(f"Seeded {inserted} account(s).")
        else:
            logger.info("Seed accounts already present, skipping.")
    finally:
        db.close()
    yield


app = FastAPI(
    title="Signal Radar API",
    version="0.1.0",
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
)
app.include_router(health.router)
app.include_router(accounts.router)
