"""
Analytics API Routes
Endpoints for the dashboard to fetch stats and history.
"""

from fastapi import APIRouter
from app.services.analytics.tracker import AnalyticsTracker
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/stats")
async def get_stats():
    """Get aggregate verification statistics."""
    tracker = AnalyticsTracker()
    return tracker.get_stats()


@router.get("/history")
async def get_history(limit: int = 50):
    """Get recent verification history."""
    tracker = AnalyticsTracker()
    events = tracker.get_events(limit=limit)
    return {"events": events, "total": len(events)}


@router.get("/preprocessing")
async def get_preprocessing_stats():
    """Get preprocessing-specific analytics (query types, claim extraction, etc.)."""
    tracker = AnalyticsTracker()
    return tracker.get_preprocessing_stats()


@router.get("/pipeline")
async def get_pipeline_stats():
    """Get per-stage pipeline performance breakdown."""
    tracker = AnalyticsTracker()
    return tracker.get_pipeline_stats()


@router.delete("/clear")
async def clear_analytics():
    """Clear all analytics data (for testing)."""
    tracker = AnalyticsTracker()
    tracker.clear()
    return {"status": "cleared"}
