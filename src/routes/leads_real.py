"""
Real leads routes using database and search engine
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from ..database.connection import get_db_session
from ..database.models import Lead as LeadModel
from ..models.lead import Lead, LeadCreate
from ..models.search import SearchQuery, SearchFilters, SearchUserPreferences
from ..search.engine import SearchEngine
from ..cache.manager import CacheManager
from ..cache.config import get_redis_client

router = APIRouter(prefix="/leads", tags=["leads"])

def get_search_engine(db: Session = Depends(get_db_session)) -> SearchEngine:
    """Dependency to get SearchEngine instance"""
    redis_client = get_redis_client()
    cache_manager = CacheManager(redis_client)
    return SearchEngine(db, cache_manager)

@router.get("/", response_model=List[Lead])
async def get_leads(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    industry: Optional[str] = None,
    status: Optional[str] = None,
    location: Optional[str] = None,
    db: Session = Depends(get_db_session)
):
    """
    Buscar leads do banco de dados com filtros opcionais
    """
    try:
        # Base query
        query = db.query(LeadModel)
        
        # Apply filters
        if industry:
            query = query.filter(LeadModel.industry.ilike(f"%{industry}%"))
        
        if status:
            query = query.filter(LeadModel.status == status)
            
        if location:
            query = query.filter(LeadModel.location.ilike(f"%{location}%"))
        
        # Apply pagination and ordering
        leads = query.order_by(LeadModel.created_at.desc()).offset(skip).limit(limit).all()
        
        return leads
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar leads: {str(e)}")

@router.get("/search", response_model=List[dict])
async def search_leads_advanced(
    q: str = Query(..., description="Texto de busca"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    industry: Optional[str] = None,
    location: Optional[str] = None,
    company_size: Optional[str] = None,
    revenue_range: Optional[str] = None,
    sort_by: str = Query("relevance", regex="^(relevance|created_at)$"),
    search_engine: SearchEngine = Depends(get_search_engine)
):
    """
    Busca avançada usando o SearchEngine
    """
    try:
        # Create search filters
        filters = SearchFilters(
            industry=industry,
            location=location,
            company_size=company_size,
            revenue_range=revenue_range
        )
        
        # Create search query
        search_query = SearchQuery(
            text=q,
            filters=filters,
            sort_by=sort_by,
            limit=limit,
            offset=offset
        )
        
        # Execute search
        results = search_engine.search_leads(search_query)
        
        # Convert to response format
        response = []
        for result in results:
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
                "score": result.relevance_score,
                "match_reasons": result.match_reasons,
                "highlighted_fields": result.highlighted_fields,
                "created_at": result.lead.indexed_at
            }
            response.append(lead_data)
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na busca: {str(e)}")

@router.get("/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=2, description="Texto parcial para sugestões"),
    limit: int = Query(10, ge=1, le=20),
    search_engine: SearchEngine = Depends(get_search_engine)
):
    """
    Obter sugestões de busca (autocomplete)
    """
    try:
        suggestions = search_engine.get_search_suggestions(q, limit=limit)
        return {"suggestions": suggestions}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter sugestões: {str(e)}")

@router.post("/", response_model=Lead)
async def create_lead(
    lead: LeadCreate,
    db: Session = Depends(get_db_session)
):
    """
    Criar novo lead no banco de dados
    """
    try:
        # Create new lead
        db_lead = LeadModel(
            user_id=1,  # TODO: Get from authenticated user
            **lead.dict()
        )
        
        db.add(db_lead)
        db.commit()
        db.refresh(db_lead)
        
        # Index the new lead
        redis_client = get_redis_client()
        cache_manager = CacheManager(redis_client)
        search_engine = SearchEngine(db, cache_manager)
        search_engine.indexer.index_lead(db_lead)
        
        return db_lead
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar lead: {str(e)}")

@router.get("/{lead_id}", response_model=Lead)
async def get_lead(
    lead_id: int,
    db: Session = Depends(get_db_session)
):
    """
    Buscar lead específico por ID
    """
    lead = db.query(LeadModel).filter(LeadModel.id == lead_id).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")
    
    return lead

@router.put("/{lead_id}", response_model=Lead)
async def update_lead(
    lead_id: int,
    lead_update: dict,
    db: Session = Depends(get_db_session)
):
    """
    Atualizar lead existente
    """
    try:
        lead = db.query(LeadModel).filter(LeadModel.id == lead_id).first()
        
        if not lead:
            raise HTTPException(status_code=404, detail="Lead não encontrado")
        
        # Update fields
        for field, value in lead_update.items():
            if hasattr(lead, field):
                setattr(lead, field, value)
        
        db.commit()
        db.refresh(lead)
        
        # Re-index the updated lead
        redis_client = get_redis_client()
        cache_manager = CacheManager(redis_client)
        search_engine = SearchEngine(db, cache_manager)
        search_engine.indexer.index_lead(lead)
        
        return lead
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar lead: {str(e)}")

@router.delete("/{lead_id}")
async def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db_session)
):
    """
    Deletar lead
    """
    try:
        lead = db.query(LeadModel).filter(LeadModel.id == lead_id).first()
        
        if not lead:
            raise HTTPException(status_code=404, detail="Lead não encontrado")
        
        # Remove from search index first
        redis_client = get_redis_client()
        cache_manager = CacheManager(redis_client)
        search_engine = SearchEngine(db, cache_manager)
        search_engine.indexer.remove_lead_from_index(lead_id)
        
        # Delete from database
        db.delete(lead)
        db.commit()
        
        return {"message": "Lead deletado com sucesso"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao deletar lead: {str(e)}")

@router.get("/stats/search")
async def get_search_stats(
    search_engine: SearchEngine = Depends(get_search_engine)
):
    """
    Obter estatísticas do sistema de busca
    """
    try:
        stats = search_engine.get_search_stats()
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas: {str(e)}")