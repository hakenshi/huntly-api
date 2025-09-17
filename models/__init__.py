# Import all models for easy access
from .auth import UserCreate, UserLogin, Token, User
from .lead import Lead, LeadCreate, LeadStatus, LeadPriority
from .campaign import Campaign, CampaignCreate, CampaignStatus
from .search import SearchFilters
from .analytics import (
    DashboardMetrics, LeadsByMonth, SourceMetrics, 
    IndustryBreakdown, PerformanceMetrics
)

__all__ = [
    # Auth models
    "UserCreate", "UserLogin", "Token", "User",
    # Lead models
    "Lead", "LeadCreate", "LeadStatus", "LeadPriority",
    # Campaign models
    "Campaign", "CampaignCreate", "CampaignStatus",
    # Search models
    "SearchFilters",
    # Analytics models
    "DashboardMetrics", "LeadsByMonth", "SourceMetrics",
    "IndustryBreakdown", "PerformanceMetrics"
]