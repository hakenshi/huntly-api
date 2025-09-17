from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, Dict, Any
from datetime import datetime

from ..database.models import UserPreferences as DBUserPreferences
from ..models.preferences import (
    UserPreferences, UserPreferencesCreate, UserPreferencesUpdate
)

class PreferencesService:
    """Service for managing user preferences"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_preferences(self, user_id: int) -> Optional[UserPreferences]:
        """Get user preferences by user ID"""
        db_preferences = self.db.query(DBUserPreferences).filter(
            DBUserPreferences.user_id == user_id
        ).first()
        
        if not db_preferences:
            return None
        
        return UserPreferences.model_validate(db_preferences)
    
    def create_user_preferences(
        self, 
        user_id: int, 
        preferences: UserPreferencesCreate
    ) -> UserPreferences:
        """Create new user preferences"""
        try:
            db_preferences = DBUserPreferences(
                user_id=user_id,
                preferred_industries=preferences.preferred_industries,
                preferred_locations=preferences.preferred_locations,
                company_size_range=preferences.company_size_range,
                revenue_range=preferences.revenue_range,
                scoring_weights=preferences.scoring_weights
            )
            
            self.db.add(db_preferences)
            self.db.commit()
            self.db.refresh(db_preferences)
            
            return UserPreferences.model_validate(db_preferences)
            
        except IntegrityError:
            self.db.rollback()
            raise ValueError("User preferences already exist")
    
    def update_user_preferences(
        self, 
        user_id: int, 
        preferences: UserPreferencesUpdate
    ) -> Optional[UserPreferences]:
        """Update existing user preferences"""
        db_preferences = self.db.query(DBUserPreferences).filter(
            DBUserPreferences.user_id == user_id
        ).first()
        
        if not db_preferences:
            return None
        
        # Update only provided fields
        update_data = preferences.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_preferences, field, value)
        
        db_preferences.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_preferences)
        
        return UserPreferences.model_validate(db_preferences)
    
    def delete_user_preferences(self, user_id: int) -> bool:
        """Delete user preferences"""
        db_preferences = self.db.query(DBUserPreferences).filter(
            DBUserPreferences.user_id == user_id
        ).first()
        
        if not db_preferences:
            return False
        
        self.db.delete(db_preferences)
        self.db.commit()
        return True
    
    def get_or_create_default_preferences(self, user_id: int) -> UserPreferences:
        """Get user preferences or create default ones if they don't exist"""
        preferences = self.get_user_preferences(user_id)
        
        if not preferences:
            default_preferences = UserPreferencesCreate()
            preferences = self.create_user_preferences(user_id, default_preferences)
        
        return preferences
    
    def apply_preferences_to_search_weights(
        self, 
        user_id: int, 
        base_weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """Apply user preferences to search ranking weights"""
        preferences = self.get_user_preferences(user_id)
        
        if not preferences or not preferences.scoring_weights:
            # Return default weights if no preferences
            return base_weights or {
                "industry_match": 0.25,
                "location_proximity": 0.15,
                "company_size": 0.1,
                "text_relevance": 0.4,
                "data_quality": 0.1
            }
        
        return preferences.scoring_weights
    
    def get_preference_filters(self, user_id: int) -> Dict[str, Any]:
        """Get user preference filters for search boosting"""
        preferences = self.get_user_preferences(user_id)
        
        if not preferences:
            return {}
        
        filters = {}
        
        if preferences.preferred_industries:
            filters["preferred_industries"] = preferences.preferred_industries
        
        if preferences.preferred_locations:
            filters["preferred_locations"] = preferences.preferred_locations
        
        if preferences.company_size_range:
            filters["company_size_range"] = preferences.company_size_range
        
        if preferences.revenue_range:
            filters["revenue_range"] = preferences.revenue_range
        
        return filters