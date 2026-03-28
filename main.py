"""Main FastAPI application entrypoint"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
import os
from app.core.config import get_settings
from app.core.logging import get_logger
from app.api.routes.verify import router as verify_router
from app.api.routes.analytics import router as analytics_router

# Initialize logger
logger = get_logger(__name__)

# Load settings
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for the FastAPI application."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.app_debug}")
    yield
    logger.info("Shutting down application")

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend for AI Hallucination Detection System",
    debug=settings.app_debug,
    lifespan=lifespan
)

# Add CORS middleware for extension communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict to extension origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(verify_router)
app.include_router(analytics_router)

# Mount dashboard static files
dashboard_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard")
if os.path.exists(dashboard_dir):
    app.mount("/dashboard", StaticFiles(directory=dashboard_dir, html=True), name="dashboard")

# Mount analytics dashboard
analytics_dashboard_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analytics-dashboard")
if os.path.exists(analytics_dashboard_dir):
    app.mount("/analytics", StaticFiles(directory=analytics_dashboard_dir, html=True), name="analytics-dashboard")

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "dashboard": "/dashboard"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.app_debug
    )
