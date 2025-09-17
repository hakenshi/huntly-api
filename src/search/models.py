"""
Search-related data models for the indexing system
"""

from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class SearchQuery(BaseModel):
    """Search query model with filters and preferences"""
    text: Optional[str] = None
    filters: Dict[str, Any] = {}
    sort_by: str = "relevance"
    limit: int = 20
    offset: int = 0
    user_preferences: Optional[Dict[str, Any]] = None

class IndexedLead(BaseModel):
    """Lead with indexing metadata"""
    id: int
    company: str
    contact: str
    email: str
    phone: Optional[str] = None
    website: Optional[str] = None
    industry: str
    location: str
    revenue: Optional[str] = None
    employees: Optional[str] = None
    description: Optional[str] = None
    keywords: List[str] = []
    
    # Indexing fields
    searchable_text: str
    search_vector: Optional[str] = None
    indexed_at: Optional[datetime] = None
    
    # Computed fields for search
    industry_tokens: List[str] = []
    location_tokens: List[str] = []
    company_tokens: List[str] = []

class SearchResult(BaseModel):
    """Search result with ranking information"""
    lead: IndexedLead
    relevance_score: float
    match_reasons: List[str] = []
    highlighted_fields: Dict[str, str] = {}

class IndexingStats(BaseModel):
    """Statistics for indexing operations"""
    total_leads: int
    indexed_leads: int
    failed_leads: int
    processing_time: float
    errors: List[str] = []