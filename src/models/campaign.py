from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class CampaignStatus(str, Enum):
    ATIVA = "Ativa"
    PAUSADA = "Pausada"
    FINALIZADA = "Finalizada"

class CampaignCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    location: Optional[str] = None
    company_size: Optional[str] = None
    revenue_range: Optional[str] = None
    search_query: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None

class Campaign(BaseModel):
    id: Optional[int] = None
    name: str
    status: CampaignStatus = CampaignStatus.ATIVA
    search_query: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    leads_found: int = 0
    emails_sent: int = 0
    responses: int = 0
    conversions: int = 0
    next_execution: Optional[str] = None
    last_execution: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}