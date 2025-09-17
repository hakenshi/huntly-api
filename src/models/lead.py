from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum

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

class LeadCreate(BaseModel):
    company: str
    contact: str
    email: EmailStr
    phone: Optional[str] = None
    industry: str
    location: str
    website: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[List[str]] = None

class Lead(BaseModel):
    id: Optional[int] = None
    company: str
    contact: str
    email: EmailStr
    phone: Optional[str] = None
    website: Optional[str] = None
    industry: str
    location: str
    revenue: Optional[str] = None
    employees: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    score: int = 0  # 0-100
    status: LeadStatus = LeadStatus.NOVO
    priority: LeadPriority = LeadPriority.MEDIA
    last_contact: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}

class RankedLead(Lead):
    """Lead with search ranking information"""
    relevance_score: float
    match_reasons: List[str] = []