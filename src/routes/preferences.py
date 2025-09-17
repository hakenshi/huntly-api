from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from ..database.connection import get_db
from ..models.preferences import (
    UserPreferences, UserPreferencesCreate, UserPreferencesUpdate,
    PreferencesAppliedSearch
)
from ..services.preferences import PreferencesService
from ..utils.auth import get_current_user_id

router = APIRouter(prefix="/preferences", tags=["preferences"])

@router.get("/", response_model=UserPreferences)
async def get_user_preferences(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get current user's preferences"""
    service = PreferencesService(db)
    preferences = service.get_user_preferences(current_user_id)
    
    if not preferences:
        # Return default preferences if none exist
        default_preferences = UserPreferencesCreate()
        preferences = service.create_user_preferences(current_user_id, default_preferences)
    
    return preferences

@router.post("/", response_model=UserPreferences, status_code=status.HTTP_201_CREATED)
async def create_user_preferences(
    preferences_data: UserPreferencesCreate,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Create user preferences"""
    service = PreferencesService(db)
    
    try:
        preferences = service.create_user_preferences(current_user_id, preferences_data)
        return preferences
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/", response_model=UserPreferences)
async def update_user_preferences(
    preferences_data: UserPreferencesUpdate,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Update user preferences"""
    service = PreferencesService(db)
    
    preferences = service.update_user_preferences(current_user_id, preferences_data)
    
    if not preferences:
        # Create preferences if they don't exist
        create_data = UserPreferencesCreate(
            preferred_industries=preferences_data.preferred_industries or [],
            preferred_locations=preferences_data.preferred_locations or [],
            company_size_range=preferences_data.company_size_range,
            revenue_range=preferences_data.revenue_range,
            scoring_weights=preferences_data.scoring_weights or {
                "industry_match": 0.25,
                "location_proximity": 0.15,
                "company_size": 0.1,
                "text_relevance": 0.4,
                "data_quality": 0.1
            }
        )
        preferences = service.create_user_preferences(current_user_id, create_data)
    
    return preferences

@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_preferences(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Delete user preferences (reset to defaults)"""
    service = PreferencesService(db)
    
    success = service.delete_user_preferences(current_user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User preferences not found"
        )

@router.get("/weights", response_model=Dict[str, float])
async def get_user_search_weights(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get user's custom search ranking weights"""
    service = PreferencesService(db)
    weights = service.apply_preferences_to_search_weights(current_user_id)
    return weights

@router.get("/filters", response_model=Dict[str, Any])
async def get_user_preference_filters(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get user's preference filters for search boosting"""
    service = PreferencesService(db)
    filters = service.get_preference_filters(current_user_id)
    return filters

@router.get("/suggestions")
async def get_preference_suggestions(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get suggestions for user preferences based on their search history"""
    # This could be enhanced to analyze user's search patterns
    # For now, return common industry and location options
    
    suggestions = {
        "industries": [
            "Tecnologia", "Saúde", "Educação", "Varejo", "Serviços Financeiros",
            "Manufatura", "Imobiliário", "Consultoria", "Marketing", "E-commerce",
            "Alimentação", "Turismo", "Logística", "Energia", "Telecomunicações"
        ],
        "locations": [
            "São Paulo, SP", "Rio de Janeiro, RJ", "Belo Horizonte, MG",
            "Brasília, DF", "Porto Alegre, RS", "Curitiba, PR", "Salvador, BA",
            "Fortaleza, CE", "Recife, PE", "Goiânia, GO", "Campinas, SP",
            "Florianópolis, SC", "Vitória, ES", "Manaus, AM", "Belém, PA"
        ],
        "company_sizes": [
            "1-10 funcionários", "11-50 funcionários", "51-200 funcionários",
            "201-500 funcionários", "501-1000 funcionários", "1000+ funcionários"
        ],
        "revenue_ranges": [
            "Até R$ 1M", "R$ 1M - R$ 5M", "R$ 5M - R$ 20M",
            "R$ 20M - R$ 100M", "R$ 100M - R$ 500M", "R$ 500M+"
        ]
    }
    
    return suggestions