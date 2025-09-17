from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from typing import List, Optional
from datetime import datetime

from ..database.connection import get_db, get_redis
from ..database.models import Lead as DBLead
from ..models.lead import Lead, LeadCreate, RankedLead
from ..models.search import SearchFilters, SearchQuery, SearchUserPreferences
from ..models.preferences import PreferencesAppliedSearch
from ..services.preferences import PreferencesService
from ..search.engine import SearchEngine
from ..cache.manager import CacheManager
from ..auth.utils import get_current_user_id

router = APIRouter(prefix="/leads", tags=["leads"])

@router.get("/", response_model=List[Lead])
async def get_leads(
    skip: int = 0,
    limit: int = 100,
    industry: Optional[str] = None,
    status: Optional[str] = None,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Buscar leads com filtros opcionais"""
    query = db.query(DBLead).filter(DBLead.user_id == current_user_id)
    
    if industry:
        query = query.filter(DBLead.industry.ilike(f"%{industry}%"))
    
    if status:
        query = query.filter(DBLead.status == status)
    
    leads = query.offset(skip).limit(limit).all()
    return [Lead.model_validate(lead) for lead in leads]

@router.post("/", response_model=Lead)
async def create_lead(
    lead: LeadCreate,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Criar novo lead"""
    db_lead = DBLead(
        user_id=current_user_id,
        **lead.model_dump()
    )
    
    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)
    
    return Lead.model_validate(db_lead)

@router.get("/{lead_id}", response_model=Lead)
async def get_lead(
    lead_id: int,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Buscar lead por ID"""
    lead = db.query(DBLead).filter(
        DBLead.id == lead_id,
        DBLead.user_id == current_user_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    
    return Lead.model_validate(lead)

@router.put("/{lead_id}", response_model=Lead)
async def update_lead(
    lead_id: int,
    lead_update: dict,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Atualizar lead"""
    lead = db.query(DBLead).filter(
        DBLead.id == lead_id,
        DBLead.user_id == current_user_id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    
    for key, value in lead_update.items():
        if hasattr(lead, key):
            setattr(lead, key, value)
    
    lead.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lead)
    
    return Lead.model_validate(lead)

@router.post("/search", response_model=List[RankedLead])
async def search_leads(
    search_query: SearchQuery,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Buscar leads com algoritmo de ranking e preferências do usuário"""
    try:
        # Initialize services
        cache_manager = CacheManager(redis_client) if redis_client else None
        search_engine = SearchEngine(db, cache_manager)
        preferences_service = PreferencesService(db)
        
        # Get user preferences if requested
        user_preferences = None
        if search_query.use_preferences:
            db_preferences = preferences_service.get_user_preferences(current_user_id)
            if db_preferences:
                # Convert to search preferences format
                user_preferences = SearchUserPreferences(
                    preferred_industries=db_preferences.preferred_industries,
                    preferred_locations=db_preferences.preferred_locations,
                    company_size_range=db_preferences.company_size_range,
                    revenue_range=db_preferences.revenue_range,
                    scoring_weights=db_preferences.scoring_weights
                )
        
        # Perform search with preferences
        search_results = search_engine.search_leads(search_query, user_preferences)
        
        # Convert to RankedLead format
        ranked_leads = []
        for result in search_results:
            # Convert IndexedLead to Lead first
            lead_data = {
                "id": result.lead.id,
                "company": result.lead.company,
                "contact": result.lead.contact,
                "email": result.lead.email,
                "phone": result.lead.phone,
                "website": result.lead.website,
                "industry": result.lead.industry,
                "location": result.lead.location,
                "revenue": result.lead.revenue,
                "employees": result.lead.employees,
                "description": result.lead.description,
                "keywords": result.lead.keywords,
                "score": int(result.relevance_score * 100),  # Convert to 0-100 scale
                "status": "Novo",  # Default status
                "priority": "Alta" if result.relevance_score > 0.8 else "Média",
                "created_at": result.lead.indexed_at or datetime.utcnow(),
                "updated_at": result.lead.indexed_at or datetime.utcnow()
            }
            
            ranked_lead = RankedLead(
                **lead_data,
                relevance_score=result.relevance_score,
                match_reasons=result.match_reasons
            )
            ranked_leads.append(ranked_lead)
        
        return ranked_leads
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na busca: {str(e)}"
        )

@router.post("/search/with-preferences", response_model=PreferencesAppliedSearch)
async def search_leads_with_preferences_info(
    search_query: SearchQuery,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Buscar leads e retornar informações sobre como as preferências foram aplicadas"""
    try:
        preferences_service = PreferencesService(db)
        
        # Get user preferences
        db_preferences = preferences_service.get_user_preferences(current_user_id)
        
        # Get preference filters and weights
        preference_filters = preferences_service.get_preference_filters(current_user_id)
        custom_weights = preferences_service.apply_preferences_to_search_weights(current_user_id)
        
        # Determine what preferences were applied
        preference_boosts = {}
        if db_preferences:
            if db_preferences.preferred_industries:
                preference_boosts["industries"] = db_preferences.preferred_industries
            if db_preferences.preferred_locations:
                preference_boosts["locations"] = db_preferences.preferred_locations
        
        return PreferencesAppliedSearch(
            query=search_query.text or "",
            preferences_applied=db_preferences is not None,
            custom_weights_used=custom_weights,
            preference_boosts=preference_boosts
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar preferências: {str(e)}"
        )

@router.get("/search/suggestions")
async def get_search_suggestions(
    q: str,
    limit: int = 10,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Obter sugestões de busca baseadas em query parcial"""
    try:
        cache_manager = CacheManager(redis_client) if redis_client else None
        search_engine = SearchEngine(db, cache_manager)
        
        suggestions = search_engine.get_search_suggestions(q, limit)
        return {"suggestions": suggestions}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter sugestões: {str(e)}"
        )

@router.get("/search/facets")
async def get_search_facets(
    q: Optional[str] = None,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Obter facetas disponíveis para filtros avançados"""
    try:
        cache_manager = CacheManager(redis_client) if redis_client else None
        
        # Check cache first
        cache_key = f"search_facets:{current_user_id}:{q or 'all'}"
        if cache_manager:
            cached_facets = cache_manager.get_cached_data(cache_key)
            if cached_facets:
                return cached_facets
        
        # Build base query for user's leads
        base_query = db.query(DBLead).filter(DBLead.user_id == current_user_id)
        
        # Apply text filter if provided
        if q:
            base_query = base_query.filter(
                or_(
                    DBLead.company.ilike(f"%{q}%"),
                    DBLead.industry.ilike(f"%{q}%"),
                    DBLead.description.ilike(f"%{q}%")
                )
            )
        
        # Get industry facets
        industry_facets = db.query(
            DBLead.industry,
            func.count(DBLead.id).label('count')
        ).filter(
            DBLead.user_id == current_user_id,
            DBLead.industry.isnot(None)
        )
        
        if q:
            industry_facets = industry_facets.filter(
                or_(
                    DBLead.company.ilike(f"%{q}%"),
                    DBLead.industry.ilike(f"%{q}%"),
                    DBLead.description.ilike(f"%{q}%")
                )
            )
        
        industry_facets = industry_facets.group_by(DBLead.industry).order_by(func.count(DBLead.id).desc()).limit(10).all()
        
        # Get location facets
        location_facets = db.query(
            DBLead.location,
            func.count(DBLead.id).label('count')
        ).filter(
            DBLead.user_id == current_user_id,
            DBLead.location.isnot(None)
        )
        
        if q:
            location_facets = location_facets.filter(
                or_(
                    DBLead.company.ilike(f"%{q}%"),
                    DBLead.industry.ilike(f"%{q}%"),
                    DBLead.description.ilike(f"%{q}%")
                )
            )
        
        location_facets = location_facets.group_by(DBLead.location).order_by(func.count(DBLead.id).desc()).limit(10).all()
        
        # Get company size facets
        size_facets = db.query(
            DBLead.employees,
            func.count(DBLead.id).label('count')
        ).filter(
            DBLead.user_id == current_user_id,
            DBLead.employees.isnot(None)
        )
        
        if q:
            size_facets = size_facets.filter(
                or_(
                    DBLead.company.ilike(f"%{q}%"),
                    DBLead.industry.ilike(f"%{q}%"),
                    DBLead.description.ilike(f"%{q}%")
                )
            )
        
        size_facets = size_facets.group_by(DBLead.employees).order_by(func.count(DBLead.id).desc()).limit(10).all()
        
        # Get revenue facets
        revenue_facets = db.query(
            DBLead.revenue,
            func.count(DBLead.id).label('count')
        ).filter(
            DBLead.user_id == current_user_id,
            DBLead.revenue.isnot(None)
        )
        
        if q:
            revenue_facets = revenue_facets.filter(
                or_(
                    DBLead.company.ilike(f"%{q}%"),
                    DBLead.industry.ilike(f"%{q}%"),
                    DBLead.description.ilike(f"%{q}%")
                )
            )
        
        revenue_facets = revenue_facets.group_by(DBLead.revenue).order_by(func.count(DBLead.id).desc()).limit(10).all()
        
        facets = {
            "industries": [{"value": item[0], "count": item[1]} for item in industry_facets if item[0]],
            "locations": [{"value": item[0], "count": item[1]} for item in location_facets if item[0]],
            "company_sizes": [{"value": item[0], "count": item[1]} for item in size_facets if item[0]],
            "revenue_ranges": [{"value": item[0], "count": item[1]} for item in revenue_facets if item[0]]
        }
        
        # Cache facets for 30 minutes
        if cache_manager:
            cache_manager.cache_data(cache_key, facets, ttl=1800)
        
        return facets
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter facetas: {str(e)}"
        )

@router.get("/search/analytics")
async def get_search_analytics(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Obter analytics e métricas de performance de busca"""
    try:
        cache_manager = CacheManager(redis_client) if redis_client else None
        search_engine = SearchEngine(db, cache_manager)
        
        # Get search engine stats
        search_stats = search_engine.get_search_stats()
        
        # Get user-specific search metrics
        total_leads = db.query(func.count(DBLead.id)).filter(DBLead.user_id == current_user_id).scalar()
        
        # Get indexed leads count
        indexed_leads = db.query(func.count(DBLead.id)).filter(
            DBLead.user_id == current_user_id,
            DBLead.indexed_at.isnot(None)
        ).scalar()
        
        # Get recent search performance (mock data for now - would be tracked in real implementation)
        recent_searches = []
        if cache_manager:
            popular_searches = cache_manager.get_popular_searches(10)
            recent_searches = [{"query": search, "count": 1} for search in popular_searches[:5]]
        
        # Calculate search coverage
        search_coverage = (indexed_leads / total_leads * 100) if total_leads > 0 else 0
        
        # Get average search response time (mock data)
        avg_response_time = 0.15  # 150ms average
        
        analytics = {
            "search_performance": {
                "total_leads": total_leads,
                "indexed_leads": indexed_leads,
                "search_coverage_percent": round(search_coverage, 2),
                "avg_response_time_ms": int(avg_response_time * 1000),
                "cache_hit_rate": search_stats.get("cache_health", {}).get("hit_rate", 0)
            },
            "popular_searches": recent_searches,
            "search_trends": {
                "daily_searches": 45,  # Mock data
                "unique_queries": 23,
                "avg_results_per_search": 12.5
            },
            "indexing_status": search_stats.get("indexing_status", {}),
            "last_updated": search_stats.get("last_updated")
        }
        
        return analytics
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter analytics: {str(e)}"
        )

@router.post("/search/advanced")
async def advanced_search_leads(
    search_query: SearchQuery,
    facet_filters: Optional[dict] = None,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Busca avançada com filtros facetados e analytics detalhados"""
    try:
        # Initialize services
        cache_manager = CacheManager(redis_client) if redis_client else None
        search_engine = SearchEngine(db, cache_manager)
        preferences_service = PreferencesService(db)
        
        # Apply facet filters to search query if provided
        if facet_filters:
            if not search_query.filters:
                search_query.filters = SearchFilters()
            
            # Apply facet filters
            if facet_filters.get("industries"):
                search_query.filters.industry = facet_filters["industries"][0]  # Take first selected
            if facet_filters.get("locations"):
                search_query.filters.location = facet_filters["locations"][0]
            if facet_filters.get("company_sizes"):
                search_query.filters.company_size = facet_filters["company_sizes"][0]
            if facet_filters.get("revenue_ranges"):
                search_query.filters.revenue_range = facet_filters["revenue_ranges"][0]
        
        # Get user preferences if requested
        user_preferences = None
        if search_query.use_preferences:
            db_preferences = preferences_service.get_user_preferences(current_user_id)
            if db_preferences:
                user_preferences = SearchUserPreferences(
                    preferred_industries=db_preferences.preferred_industries,
                    preferred_locations=db_preferences.preferred_locations,
                    company_size_range=db_preferences.company_size_range,
                    revenue_range=db_preferences.revenue_range,
                    scoring_weights=db_preferences.scoring_weights
                )
        
        # Track search start time
        search_start = datetime.utcnow()
        
        # Perform search
        search_results = search_engine.search_leads(search_query, user_preferences)
        
        # Calculate search time
        search_time_ms = int((datetime.utcnow() - search_start).total_seconds() * 1000)
        
        # Convert to RankedLead format
        ranked_leads = []
        for result in search_results:
            lead_data = {
                "id": result.lead.id,
                "company": result.lead.company,
                "contact": result.lead.contact,
                "email": result.lead.email,
                "phone": result.lead.phone,
                "website": result.lead.website,
                "industry": result.lead.industry,
                "location": result.lead.location,
                "revenue": result.lead.revenue,
                "employees": result.lead.employees,
                "description": result.lead.description,
                "keywords": result.lead.keywords,
                "score": int(result.relevance_score * 100),
                "status": "Novo",
                "priority": "Alta" if result.relevance_score > 0.8 else "Média",
                "created_at": result.lead.indexed_at or datetime.utcnow(),
                "updated_at": result.lead.indexed_at or datetime.utcnow()
            }
            
            ranked_lead = RankedLead(
                **lead_data,
                relevance_score=result.relevance_score,
                match_reasons=result.match_reasons
            )
            ranked_leads.append(ranked_lead)
        
        # Get result facets for refinement
        result_facets = {}
        if ranked_leads:
            # Calculate facets from results
            industries = {}
            locations = {}
            sizes = {}
            
            for lead in ranked_leads:
                if lead.industry:
                    industries[lead.industry] = industries.get(lead.industry, 0) + 1
                if lead.location:
                    locations[lead.location] = locations.get(lead.location, 0) + 1
                if lead.employees:
                    sizes[lead.employees] = sizes.get(lead.employees, 0) + 1
            
            result_facets = {
                "industries": [{"value": k, "count": v} for k, v in sorted(industries.items(), key=lambda x: x[1], reverse=True)[:5]],
                "locations": [{"value": k, "count": v} for k, v in sorted(locations.items(), key=lambda x: x[1], reverse=True)[:5]],
                "company_sizes": [{"value": k, "count": v} for k, v in sorted(sizes.items(), key=lambda x: x[1], reverse=True)[:5]]
            }
        
        return {
            "results": ranked_leads,
            "total_results": len(ranked_leads),
            "search_time_ms": search_time_ms,
            "facets": result_facets,
            "applied_filters": {
                "text": search_query.text,
                "filters": search_query.filters.model_dump() if search_query.filters else {},
                "facet_filters": facet_filters or {}
            },
            "preferences_applied": user_preferences is not None
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na busca avançada: {str(e)}"
        )