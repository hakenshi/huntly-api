from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict
from datetime import datetime

class UserPreferencesCreate(BaseModel):
    """Model for creating user preferences"""
    preferred_industries: Optional[List[str]] = []
    preferred_locations: Optional[List[str]] = []
    company_size_range: Optional[str] = None
    revenue_range: Optional[str] = None
    scoring_weights: Optional[Dict[str, float]] = {
        "industry_match": 0.25,
        "location_proximity": 0.15,
        "company_size": 0.1,
        "text_relevance": 0.4,
        "data_quality": 0.1
    }
    
    @field_validator('scoring_weights')
    @classmethod
    def validate_scoring_weights(cls, v):
        if v is None:
            return {
                "industry_match": 0.25,
                "location_proximity": 0.15,
                "company_size": 0.1,
                "text_relevance": 0.4,
                "data_quality": 0.1
            }
        
        # Validate that weights sum to approximately 1.0
        total = sum(v.values())
        if not (0.95 <= total <= 1.05):
            raise ValueError('Scoring weights must sum to approximately 1.0')
        
        # Validate individual weights are between 0 and 1
        for key, weight in v.items():
            if not (0 <= weight <= 1):
                raise ValueError(f'Weight for {key} must be between 0 and 1')
        
        return v

class UserPreferencesUpdate(BaseModel):
    """Model for updating user preferences"""
    preferred_industries: Optional[List[str]] = None
    preferred_locations: Optional[List[str]] = None
    company_size_range: Optional[str] = None
    revenue_range: Optional[str] = None
    scoring_weights: Optional[Dict[str, float]] = None
    
    @field_validator('scoring_weights')
    @classmethod
    def validate_scoring_weights(cls, v):
        if v is None:
            return v
        
        # Validate that weights sum to approximately 1.0
        total = sum(v.values())
        if not (0.95 <= total <= 1.05):
            raise ValueError('Scoring weights must sum to approximately 1.0')
        
        # Validate individual weights are between 0 and 1
        for key, weight in v.items():
            if not (0 <= weight <= 1):
                raise ValueError(f'Weight for {key} must be between 0 and 1')
        
        return v

class UserPreferences(BaseModel):
    """Model for user preferences response"""
    id: int
    user_id: int
    preferred_industries: List[str]
    preferred_locations: List[str]
    company_size_range: Optional[str] = None
    revenue_range: Optional[str] = None
    scoring_weights: Dict[str, float]
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

class PreferencesAppliedSearch(BaseModel):
    """Model for search results with applied preferences"""
    query: str
    preferences_applied: bool
    custom_weights_used: Dict[str, float]
    preference_boosts: Dict[str, List[str]]  # What preferences were matched