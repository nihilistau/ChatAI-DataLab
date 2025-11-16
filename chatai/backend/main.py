from __future__ import annotations

"""FastAPI entry point for the ChatAI backend."""
# @tag:backend,api

# --- Imports -----------------------------------------------------------------
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.commands import router as commands_router
from app.api.control import router as control_router
from app.api.elements import router as elements_router
from app.api.routes import router as chat_router
from app.config import get_settings
from app.database import Base, get_engine

# --- Settings & metadata ------------------------------------------------------
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Provision application resources for the FastAPI lifespan."""

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="ChatAI FastAPI", version="0.1.0", lifespan=lifespan)


# --- Middleware ---------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Routers ------------------------------------------------------------------
app.include_router(chat_router, prefix="/api")
app.include_router(control_router, prefix="/api")
app.include_router(elements_router, prefix="/api")
app.include_router(commands_router, prefix="/api")


# --- Diagnostics --------------------------------------------------------------
@app.get("/health", tags=["health"])
async def healthcheck() -> dict[str, str]:
    """Provide a lightweight readiness probe for orchestrators."""

    return {"status": "ok", "environment": settings.environment}
