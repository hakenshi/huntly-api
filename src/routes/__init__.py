"""
Routes module for Huntly MVP
API endpoints for leads, campaigns, and analytics
"""

from .leads import router as leads_router
from .campaigns import router as campaigns_router
from .analytics import router as analytics_router

__all__ = [
    "leads_router",
    "campaigns_router", 
    "analytics_router"
]