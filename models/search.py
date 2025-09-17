from pydantic import BaseModel
from typing import Optional, List, Dict

class SearchFilters(BaseModel):
    industry: Optional[str] = None
    location: Optional[str] = None
    company_size: Optional[str] = None
    revenue_range: Optional[str] = None
    keywords: Optional[List[str]] = None

class SearchQuery(BaseModel):
    text: Optional[str] = None
    filters: SearchFilters = SearchFilters()
    sort_by: str = "relevance"
    limit: int = 20
    offset: int = 0

class UserPreferences(BaseModel):
    preferred_industries: List[str] = []
    preferred_locations: List[str] = []
    company_size_range: Optional[str] = None
    revenue_range: Optional[str] = None
    scoring_weights: Dict[str, float] = {
        "industry_match": 0.25,
        "location_proximity": 0.15,
        "company_size": 0.1,
        "text_relevance": 0.4,
        "data_quality": 0.1
    }
    
    model_config = {"from_attributes": True}