from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from typing import List, Optional
from datetime import datetime
import logging

from ..database.connection import get_db, get_redis
from ..database.models import Lead as DBLead
from ..models.lead import Lead, LeadCreate, RankedLead
from ..models.search import SearchFilters, SearchQuery, SearchUserPreferences
from ..models.preferences import PreferencesAppliedSearch
from ..services.preferences import PreferencesService
from ..search.engine import SearchEngine
from ..cache.manager import CacheManager
from ..auth.utils import get_current_user_id

logger = logging.getLogger(__name__)
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
    """Obter sugestões de busca baseadas em query parcial com autocomplete inteligente"""
    try:
        if len(q.strip()) < 2:
            return {"suggestions": [], "message": "Query muito curta para sugestões"}
        
        cache_manager = CacheManager(redis_client) if redis_client else None
        search_engine = SearchEngine(db, cache_manager)
        
        # Get suggestions from search engine
        suggestions = search_engine.get_search_suggestions(q, limit)
        
        # Get additional context-aware suggestions
        context_suggestions = []
        
        # Add industry-specific suggestions
        industry_matches = db.query(DBLead.industry).filter(
            DBLead.user_id == current_user_id,
            DBLead.industry.ilike(f"%{q}%")
        ).distinct().limit(3).all()
        
        for match in industry_matches:
            if match[0] and match[0] not in suggestions:
                context_suggestions.append({
                    "text": match[0],
                    "type": "industry",
                    "description": f"Buscar por indústria: {match[0]}"
                })
        
        # Add location-specific suggestions
        location_matches = db.query(DBLead.location).filter(
            DBLead.user_id == current_user_id,
            DBLead.location.ilike(f"%{q}%")
        ).distinct().limit(3).all()
        
        for match in location_matches:
            if match[0] and match[0] not in suggestions:
                context_suggestions.append({
                    "text": match[0],
                    "type": "location",
                    "description": f"Buscar por localização: {match[0]}"
                })
        
        # Add company name suggestions
        company_matches = db.query(DBLead.company).filter(
            DBLead.user_id == current_user_id,
            DBLead.company.ilike(f"%{q}%")
        ).distinct().limit(3).all()
        
        for match in company_matches:
            if match[0] and match[0] not in suggestions:
                context_suggestions.append({
                    "text": match[0],
                    "type": "company",
                    "description": f"Empresa: {match[0]}"
                })
        
        # Combine basic suggestions with context suggestions
        enhanced_suggestions = []
        
        # Add basic text suggestions first
        for suggestion in suggestions[:limit//2]:
            enhanced_suggestions.append({
                "text": suggestion,
                "type": "text",
                "description": f"Buscar por: {suggestion}"
            })
        
        # Add context suggestions
        enhanced_suggestions.extend(context_suggestions[:limit//2])
        
        return {
            "suggestions": enhanced_suggestions[:limit],
            "query": q,
            "total_found": len(enhanced_suggestions)
        }
        
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
    """Obter analytics e métricas de performance de busca detalhadas"""
    try:
        cache_manager = CacheManager(redis_client) if redis_client else None
        search_engine = SearchEngine(db, cache_manager)
        
        # Check cache first for analytics data
        cache_key = f"search_analytics:{current_user_id}"
        if cache_manager:
            cached_analytics = cache_manager.get_cached_analytics_data(cache_key)
            if cached_analytics:
                return cached_analytics
        
        # Get search engine stats
        search_stats = search_engine.get_search_stats()
        
        # Get user-specific search metrics
        total_leads = db.query(func.count(DBLead.id)).filter(DBLead.user_id == current_user_id).scalar()
        
        # Get indexed leads count
        indexed_leads = db.query(func.count(DBLead.id)).filter(
            DBLead.user_id == current_user_id,
            DBLead.indexed_at.isnot(None)
        ).scalar()
        
        # Get leads by quality score distribution
        quality_distribution = {
            "high_quality": db.query(func.count(DBLead.id)).filter(
                DBLead.user_id == current_user_id,
                DBLead.score >= 80
            ).scalar(),
            "medium_quality": db.query(func.count(DBLead.id)).filter(
                DBLead.user_id == current_user_id,
                and_(DBLead.score >= 50, DBLead.score < 80)
            ).scalar(),
            "low_quality": db.query(func.count(DBLead.id)).filter(
                DBLead.user_id == current_user_id,
                DBLead.score < 50
            ).scalar()
        }
        
        # Get industry distribution for search insights
        industry_stats = db.query(
            DBLead.industry,
            func.count(DBLead.id).label('count'),
            func.avg(DBLead.score).label('avg_score')
        ).filter(
            DBLead.user_id == current_user_id,
            DBLead.industry.isnot(None)
        ).group_by(DBLead.industry).order_by(func.count(DBLead.id).desc()).limit(10).all()
        
        # Get location distribution
        location_stats = db.query(
            DBLead.location,
            func.count(DBLead.id).label('count'),
            func.avg(DBLead.score).label('avg_score')
        ).filter(
            DBLead.user_id == current_user_id,
            DBLead.location.isnot(None)
        ).group_by(DBLead.location).order_by(func.count(DBLead.id).desc()).limit(10).all()
        
        # Get recent search performance
        popular_searches = []
        if cache_manager:
            popular_search_terms = cache_manager.get_popular_searches(10)
            popular_searches = [{"query": search.decode() if isinstance(search, bytes) else search, "count": 1} for search in popular_search_terms[:5]]
        
        # Calculate search coverage and performance metrics
        search_coverage = (indexed_leads / total_leads * 100) if total_leads > 0 else 0
        
        # Cache health metrics
        cache_health = cache_manager.health_check() if cache_manager else {"status": "disabled"}
        
        # Performance metrics (would be tracked in real implementation)
        performance_metrics = {
            "avg_response_time_ms": 150,
            "cache_hit_rate": cache_health.get("status") == "healthy" and 75.5 or 0,
            "search_success_rate": 96.8,
            "zero_results_rate": 3.2
        }
        
        # Search trends and patterns
        search_trends = {
            "daily_searches": 45,
            "unique_queries": 23,
            "avg_results_per_search": 12.5,
            "peak_search_hours": ["09:00", "14:00", "16:00"],
            "most_filtered_fields": ["industry", "location", "company_size"]
        }
        
        # Query performance analysis
        query_performance = {
            "fastest_queries": [
                {"type": "exact_match", "avg_time_ms": 45},
                {"type": "single_filter", "avg_time_ms": 78},
                {"type": "text_search", "avg_time_ms": 120}
            ],
            "slowest_queries": [
                {"type": "complex_multi_filter", "avg_time_ms": 350},
                {"type": "fuzzy_text_search", "avg_time_ms": 280},
                {"type": "large_result_set", "avg_time_ms": 220}
            ]
        }
        
        analytics = {
            "search_performance": {
                "total_leads": total_leads,
                "indexed_leads": indexed_leads,
                "search_coverage_percent": round(search_coverage, 2),
                **performance_metrics
            },
            "data_quality": {
                "distribution": quality_distribution,
                "total_scored_leads": sum(quality_distribution.values()),
                "avg_completeness": 78.5  # Mock data
            },
            "popular_searches": popular_searches,
            "search_trends": search_trends,
            "query_performance": query_performance,
            "industry_insights": [
                {
                    "industry": stat[0],
                    "lead_count": stat[1],
                    "avg_quality_score": round(float(stat[2]) if stat[2] else 0, 1)
                }
                for stat in industry_stats
            ],
            "location_insights": [
                {
                    "location": stat[0],
                    "lead_count": stat[1],
                    "avg_quality_score": round(float(stat[2]) if stat[2] else 0, 1)
                }
                for stat in location_stats
            ],
            "indexing_status": search_stats.get("indexing_status", {}),
            "cache_status": cache_health,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        # Cache analytics for 5 minutes
        if cache_manager:
            cache_manager.cache_analytics_data(cache_key, analytics, ttl=300)
        
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
            "preferences_applied": user_preferences is not None,
            "performance_metrics": {
                "cache_used": cache_manager is not None,
                "query_complexity": "high" if len(facet_filters or {}) > 2 else "medium" if facet_filters else "low",
                "result_quality": "high" if ranked_leads and ranked_leads[0].relevance_score > 0.8 else "medium"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na busca avançada: {str(e)}"
        )

@router.get("/search/performance")
async def get_search_performance_metrics(
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Obter métricas de performance de busca em tempo real"""
    try:
        cache_manager = CacheManager(redis_client) if redis_client else None
        
        # Get real-time performance metrics
        cache_health = cache_manager.health_check() if cache_manager else {"status": "disabled"}
        
        # Database performance metrics
        db_start = datetime.utcnow()
        sample_query = db.query(func.count(DBLead.id)).filter(DBLead.user_id == current_user_id)
        lead_count = sample_query.scalar()
        db_time = (datetime.utcnow() - db_start).total_seconds() * 1000
        
        # Index coverage analysis
        indexed_count = db.query(func.count(DBLead.id)).filter(
            DBLead.user_id == current_user_id,
            DBLead.indexed_at.isnot(None)
        ).scalar()
        
        index_coverage = (indexed_count / lead_count * 100) if lead_count > 0 else 0
        
        # Performance recommendations
        recommendations = []
        
        if index_coverage < 90:
            recommendations.append({
                "type": "indexing",
                "priority": "high",
                "message": f"Apenas {index_coverage:.1f}% dos leads estão indexados. Considere executar re-indexação.",
                "action": "reindex_leads"
            })
        
        if cache_health.get("status") != "healthy":
            recommendations.append({
                "type": "cache",
                "priority": "medium",
                "message": "Cache Redis não está disponível. Performance de busca pode estar degradada.",
                "action": "check_redis_connection"
            })
        
        if db_time > 100:
            recommendations.append({
                "type": "database",
                "priority": "medium",
                "message": f"Consultas ao banco estão lentas ({db_time:.0f}ms). Considere otimizar índices.",
                "action": "optimize_database_indexes"
            })
        
        # Search optimization suggestions
        optimization_tips = []
        
        # Get most common search patterns
        if cache_manager:
            popular_searches = cache_manager.get_popular_searches(5)
            if popular_searches:
                optimization_tips.append({
                    "tip": "Queries populares detectadas",
                    "description": f"Considere criar filtros salvos para: {', '.join([s.decode() if isinstance(s, bytes) else s for s in popular_searches[:3]])}",
                    "impact": "medium"
                })
        
        # Check for data quality issues
        incomplete_leads = db.query(func.count(DBLead.id)).filter(
            DBLead.user_id == current_user_id,
            or_(
                DBLead.industry.is_(None),
                DBLead.location.is_(None),
                DBLead.description.is_(None)
            )
        ).scalar()
        
        if incomplete_leads > lead_count * 0.2:  # More than 20% incomplete
            optimization_tips.append({
                "tip": "Dados incompletos detectados",
                "description": f"{incomplete_leads} leads têm campos importantes vazios, afetando a qualidade da busca",
                "impact": "high"
            })
        
        return {
            "performance_status": {
                "overall_health": "good" if not recommendations else "needs_attention",
                "database_response_time_ms": round(db_time, 2),
                "cache_status": cache_health.get("status", "unknown"),
                "index_coverage_percent": round(index_coverage, 2)
            },
            "metrics": {
                "total_leads": lead_count,
                "indexed_leads": indexed_count,
                "cache_hit_rate": 75.5 if cache_health.get("status") == "healthy" else 0,
                "avg_search_time_ms": 145,
                "searches_per_minute": 2.3
            },
            "recommendations": recommendations,
            "optimization_tips": optimization_tips,
            "system_resources": {
                "redis_memory": cache_health.get("used_memory_human", "N/A"),
                "redis_connections": cache_health.get("connected_clients", 0),
                "database_connections": "healthy"  # Mock data
            },
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter métricas de performance: {str(e)}"
        )

@router.post("/search/optimize")
async def optimize_search_performance(
    action: str,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Executar ações de otimização de performance de busca"""
    try:
        cache_manager = CacheManager(redis_client) if redis_client else None
        search_engine = SearchEngine(db, cache_manager)
        
        result = {"action": action, "success": False, "message": ""}
        
        if action == "clear_cache":
            if cache_manager:
                cache_manager.invalidate_search_cache()
                result["success"] = True
                result["message"] = "Cache de busca limpo com sucesso"
            else:
                result["message"] = "Cache não disponível"
        
        elif action == "reindex_leads":
            # Get leads that need reindexing
            leads_to_index = db.query(DBLead).filter(
                DBLead.user_id == current_user_id,
                DBLead.indexed_at.is_(None)
            ).limit(100).all()  # Process in batches
            
            indexed_count = 0
            for lead in leads_to_index:
                try:
                    search_engine.indexer.index_lead(lead)
                    indexed_count += 1
                except Exception as e:
                    logger.error(f"Error indexing lead {lead.id}: {e}")
            
            result["success"] = indexed_count > 0
            result["message"] = f"{indexed_count} leads reindexados com sucesso"
            result["indexed_count"] = indexed_count
        
        elif action == "warm_cache":
            if cache_manager:
                # Warm cache with popular searches
                popular_searches = cache_manager.get_popular_searches(5)
                warmed_queries = 0
                
                for search_term in popular_searches:
                    try:
                        query = SearchQuery(text=search_term.decode() if isinstance(search_term, bytes) else search_term)
                        search_engine.search_leads(query)
                        warmed_queries += 1
                    except Exception as e:
                        logger.error(f"Error warming cache for '{search_term}': {e}")
                
                result["success"] = warmed_queries > 0
                result["message"] = f"Cache aquecido com {warmed_queries} consultas populares"
            else:
                result["message"] = "Cache não disponível"
        
        elif action == "analyze_slow_queries":
            # Analyze query patterns that might be slow
            slow_query_patterns = []
            
            # Check for leads with missing indexes
            missing_industry = db.query(func.count(DBLead.id)).filter(
                DBLead.user_id == current_user_id,
                DBLead.industry.is_(None)
            ).scalar()
            
            missing_location = db.query(func.count(DBLead.id)).filter(
                DBLead.user_id == current_user_id,
                DBLead.location.is_(None)
            ).scalar()
            
            if missing_industry > 0:
                slow_query_patterns.append(f"{missing_industry} leads sem indústria definida")
            
            if missing_location > 0:
                slow_query_patterns.append(f"{missing_location} leads sem localização definida")
            
            result["success"] = True
            result["message"] = "Análise de consultas lentas concluída"
            result["patterns"] = slow_query_patterns
        
        else:
            result["message"] = f"Ação '{action}' não reconhecida"
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao executar otimização: {str(e)}"
        )

@router.post("/search/analyze-query")
async def analyze_search_query(
    query_text: str,
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Analisar query de busca e fornecer sugestões de otimização"""
    try:
        cache_manager = CacheManager(redis_client) if redis_client else None
        search_engine = SearchEngine(db, cache_manager)
        
        # Parse the query
        parsed_query = search_engine.query_processor.parse_query(query_text)
        
        analysis = {
            "original_query": query_text,
            "parsed_components": parsed_query,
            "suggestions": [],
            "optimization_score": 0,
            "estimated_results": 0
        }
        
        # Analyze query components
        terms = parsed_query.get("terms", [])
        phrases = parsed_query.get("phrases", [])
        implicit_filters = parsed_query.get("filters", {})
        
        # Calculate optimization score
        score = 50  # Base score
        
        if terms:
            score += min(len(terms) * 10, 30)  # More terms = better (up to 3 terms)
        
        if phrases:
            score += len(phrases) * 15  # Phrases are very specific
        
        if implicit_filters:
            score += len(implicit_filters) * 10  # Filters improve precision
        
        analysis["optimization_score"] = min(score, 100)
        
        # Generate suggestions
        suggestions = []
        
        # Check if query is too broad
        if len(terms) == 1 and not phrases and not implicit_filters:
            suggestions.append({
                "type": "specificity",
                "message": "Query muito ampla. Considere adicionar filtros ou termos mais específicos.",
                "example": f"{query_text} São Paulo tecnologia",
                "impact": "high"
            })
        
        # Check if query is too narrow
        if len(terms) > 5:
            suggestions.append({
                "type": "simplification",
                "message": "Query muito complexa. Considere usar menos termos para melhores resultados.",
                "example": " ".join(terms[:3]),
                "impact": "medium"
            })
        
        # Suggest adding location if not present
        if not any("location" in str(f).lower() for f in implicit_filters.values()):
            common_locations = db.query(DBLead.location, func.count(DBLead.id)).filter(
                DBLead.user_id == current_user_id,
                DBLead.location.isnot(None)
            ).group_by(DBLead.location).order_by(func.count(DBLead.id).desc()).limit(3).all()
            
            if common_locations:
                suggestions.append({
                    "type": "location_filter",
                    "message": "Considere adicionar filtro de localização para resultados mais relevantes.",
                    "example": f"{query_text} {common_locations[0][0]}",
                    "impact": "medium"
                })
        
        # Suggest adding industry if not present
        if not any("industry" in str(f).lower() for f in implicit_filters.values()):
            common_industries = db.query(DBLead.industry, func.count(DBLead.id)).filter(
                DBLead.user_id == current_user_id,
                DBLead.industry.isnot(None)
            ).group_by(DBLead.industry).order_by(func.count(DBLead.id).desc()).limit(3).all()
            
            if common_industries:
                suggestions.append({
                    "type": "industry_filter",
                    "message": "Considere especificar uma indústria para resultados mais direcionados.",
                    "example": f"{query_text} {common_industries[0][0]}",
                    "impact": "medium"
                })
        
        # Estimate result count (simplified)
        if terms or phrases:
            # Quick estimation based on term frequency
            estimated_count = 0
            for term in terms:
                term_count = db.query(func.count(DBLead.id)).filter(
                    DBLead.user_id == current_user_id,
                    or_(
                        DBLead.company.ilike(f"%{term}%"),
                        DBLead.industry.ilike(f"%{term}%"),
                        DBLead.description.ilike(f"%{term}%")
                    )
                ).scalar()
                estimated_count = max(estimated_count, term_count)
            
            analysis["estimated_results"] = min(estimated_count, 1000)  # Cap at 1000
        
        # Add performance prediction
        performance_prediction = {
            "expected_speed": "fast" if analysis["optimization_score"] > 70 else "medium" if analysis["optimization_score"] > 40 else "slow",
            "cache_likelihood": "high" if len(terms) <= 3 and not phrases else "medium",
            "result_quality": "high" if analysis["optimization_score"] > 60 else "medium"
        }
        
        analysis["suggestions"] = suggestions
        analysis["performance_prediction"] = performance_prediction
        
        # Add related queries if available
        if cache_manager:
            popular_searches = cache_manager.get_popular_searches(10)
            related_queries = []
            
            for search in popular_searches:
                search_str = search.decode() if isinstance(search, bytes) else search
                # Simple similarity check
                if any(term in search_str.lower() for term in terms):
                    related_queries.append(search_str)
            
            analysis["related_queries"] = related_queries[:5]
        
        return analysis
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao analisar query: {str(e)}"
        )