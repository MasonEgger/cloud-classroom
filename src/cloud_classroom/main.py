"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cloud_classroom.api.v1 import auth, workshops, resources
from cloud_classroom.config import settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_title,
        description=settings.app_description,
        version=settings.app_version,
        debug=settings.debug,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint."""
        return {"message": "Welcome to Cloud Classroom"}

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    # Include routers
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(workshops.router, prefix="/api/v1")
    app.include_router(resources.router, prefix="/api/v1/workshops", tags=["resources"])

    return app


app = create_app()
