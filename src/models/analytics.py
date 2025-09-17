from pydantic import BaseModel

class DashboardMetrics(BaseModel):
    total_leads: int
    conversion_rate: float
    qualified_leads: int
    average_roi: float

class LeadsByMonth(BaseModel):
    month: str
    leads: int
    qualified: int

class SourceMetrics(BaseModel):
    source: str
    leads: int
    percentage: float

class IndustryBreakdown(BaseModel):
    industry: str
    count: int

class PerformanceMetrics(BaseModel):
    emails_sent: int
    open_rate: float
    click_rate: float
    calls_made: int