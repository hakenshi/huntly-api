from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

# Auth Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 3:
            raise ValueError('Senha deve ter pelo menos 3 caracteres')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Nome deve ter pelo menos 2 caracteres')
        return v.strip()

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    email: str
    name: str

# Lead Models
class LeadStatus(str, Enum):
    NOVO = "Novo"
    CONTATADO = "Contatado"
    QUALIFICADO = "Qualificado"
    EM_NEGOCIACAO = "Em Negociação"
    PROPOSTA_ENVIADA = "Proposta Enviada"
    CONVERTIDO = "Convertido"
    PERDIDO = "Perdido"

class LeadPriority(str, Enum):
    ALTA = "Alta"
    MEDIA = "Média"
    BAIXA = "Baixa"

class Lead(BaseModel):
    id: Optional[int] = None
    company: str
    contact: str
    email: EmailStr
    phone: Optional[str] = None
    industry: str
    location: str
    score: int  # 0-100
    status: LeadStatus
    priority: LeadPriority
    revenue: Optional[str] = None
    employees: Optional[str] = None
    last_contact: Optional[datetime] = None
    created_at: Optional[datetime] = None

class LeadCreate(BaseModel):
    company: str
    contact: str
    email: EmailStr
    phone: Optional[str] = None
    industry: str
    location: str

# Campaign Models
class CampaignStatus(str, Enum):
    ATIVA = "Ativa"
    PAUSADA = "Pausada"
    FINALIZADA = "Finalizada"

class Campaign(BaseModel):
    id: Optional[int] = None
    name: str
    status: CampaignStatus
    leads_found: int = 0
    emails_sent: int = 0
    responses: int = 0
    conversions: int = 0
    created_at: Optional[datetime] = None
    next_execution: Optional[str] = None

class CampaignCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    location: Optional[str] = None
    company_size: Optional[str] = None
    revenue_range: Optional[str] = None

# Search Models
class SearchFilters(BaseModel):
    industry: Optional[str] = None
    location: Optional[str] = None
    company_size: Optional[str] = None
    revenue_range: Optional[str] = None
    keywords: Optional[List[str]] = None

# Analytics Models
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
