"""
FastAPI Application Factory
ADR-009: Separation of Concerns, database-driven configuration
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cad_services.api.database import close_db, init_db
from cad_services.api.routers import (
    calculations,
    health,
    models,
    projects,
    rooms,
    upload,
    windows,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    await init_db()
    yield
    await close_db()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="CAD-Hub API",
        description="BIM/CAD Analysis Platform - Database-driven, ADR-009 compliant",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(
        projects.router,
        prefix="/api/v1/projects",
        tags=["Projects"],
    )
    app.include_router(
        models.router,
        prefix="/api/v1/models",
        tags=["Models"],
    )
    app.include_router(
        rooms.router,
        prefix="/api/v1/rooms",
        tags=["Rooms"],
    )
    app.include_router(
        windows.router,
        prefix="/api/v1/windows",
        tags=["Windows"],
    )
    app.include_router(
        calculations.router,
        prefix="/api/v1/calculations",
        tags=["Calculations"],
    )
    app.include_router(
        upload.router,
        prefix="/api/v1/upload",
        tags=["Upload"],
    )

    return app


# Create default app instance
app = create_app()
