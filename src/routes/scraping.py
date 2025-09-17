"""
API routes for lead scraping functionality
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from ..database.connection import get_db_session
from ..cache.manager import CacheManager
from ..cache.config import get_redis_client
from ..scraping.manager import ScrapingManager
from ..scraping.models import (
    ScrapingConfig, ScrapingJob, ScrapingSource, ScrapingStatus,
    ScrapedLead, ScrapingResult
)
from ..auth.middleware import get_current_user

router = APIRouter(prefix="/scraping", tags=["scraping"])

def get_scraping_manager(db: Session = Depends(get_db_session)) -> ScrapingManager:
    """Dependency to get ScrapingManager instance"""
    redis_client = get_redis_client()
    cache_manager = CacheManager(redis_client)
    return ScrapingManager(db, cache_manager)

@router.post("/start", response_model=ScrapingJob)
async def start_scraping_job(
    config: ScrapingConfig,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    scraping_manager: ScrapingManager = Depends(get_scraping_manager)
):
    """
    Iniciar um novo job de scraping de leads
    """
    try:
        # Validate config
        if not config.search_query or len(config.search_query.strip()) < 2:
            raise HTTPException(
                status_code=400, 
                detail="Query de busca deve ter pelo menos 2 caracteres"
            )
        
        if config.max_results > 1000:
            raise HTTPException(
                status_code=400,
                detail="Máximo de 1000 resultados por job"
            )
        
        # Start scraping job
        job = await scraping_manager.start_scraping_job(
            user_id=current_user["user_id"],
            config=config
        )
        
        return job
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar scraping: {str(e)}")

@router.get("/jobs", response_model=List[ScrapingJob])
async def get_scraping_jobs(
    status: Optional[ScrapingStatus] = None,
    current_user: dict = Depends(get_current_user),
    scraping_manager: ScrapingManager = Depends(get_scraping_manager)
):
    """
    Listar jobs de scraping do usuário
    """
    try:
        jobs = scraping_manager.get_active_jobs(user_id=current_user["user_id"])
        
        if status:
            jobs = [job for job in jobs if job.status == status]
        
        return jobs
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar jobs: {str(e)}")

@router.get("/jobs/{job_id}", response_model=ScrapingJob)
async def get_scraping_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    scraping_manager: ScrapingManager = Depends(get_scraping_manager)
):
    """
    Obter detalhes de um job específico
    """
    try:
        job = scraping_manager.get_job_status(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job não encontrado")
        
        # Check if user owns this job
        if job.user_id != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Acesso negado")
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter job: {str(e)}")

@router.post("/jobs/{job_id}/cancel")
async def cancel_scraping_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    scraping_manager: ScrapingManager = Depends(get_scraping_manager)
):
    """
    Cancelar um job de scraping em execução
    """
    try:
        job = scraping_manager.get_job_status(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job não encontrado")
        
        # Check if user owns this job
        if job.user_id != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Acesso negado")
        
        success = await scraping_manager.cancel_job(job_id)
        
        if not success:
            raise HTTPException(
                status_code=400, 
                detail="Job não pode ser cancelado (não está em execução)"
            )
        
        return {"message": "Job cancelado com sucesso"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao cancelar job: {str(e)}")

@router.get("/suggestions")
async def get_scraping_suggestions(
    query: str = Query(..., min_length=2, description="Query de busca"),
    scraping_manager: ScrapingManager = Depends(get_scraping_manager)
):
    """
    Obter sugestões para configuração de scraping
    """
    try:
        suggestions = await scraping_manager.get_scraping_suggestions(query)
        return suggestions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter sugestões: {str(e)}")

@router.get("/sources")
async def get_available_sources():
    """
    Listar fontes de scraping disponíveis
    """
    sources = [
        {
            "id": ScrapingSource.GOOGLE_MAPS,
            "name": "Google Maps",
            "description": "Empresas locais e informações de contato",
            "best_for": ["empresas locais", "serviços", "comércio"],
            "data_quality": "alta",
            "speed": "rápida"
        },
        {
            "id": ScrapingSource.LINKEDIN,
            "name": "LinkedIn",
            "description": "Empresas e profissionais (limitado)",
            "best_for": ["empresas B2B", "serviços profissionais", "startups"],
            "data_quality": "muito alta",
            "speed": "lenta",
            "note": "Requer autenticação ou API oficial"
        },
        {
            "id": ScrapingSource.COMPANY_WEBSITE,
            "name": "Sites de Empresas",
            "description": "Informações diretas dos sites das empresas",
            "best_for": ["contatos diretos", "informações detalhadas"],
            "data_quality": "variável",
            "speed": "média"
        }
    ]
    
    return {"sources": sources}

@router.get("/stats")
async def get_scraping_stats(
    current_user: dict = Depends(get_current_user),
    scraping_manager: ScrapingManager = Depends(get_scraping_manager)
):
    """
    Obter estatísticas de scraping
    """
    try:
        stats = scraping_manager.get_scraping_stats()
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas: {str(e)}")

@router.post("/test")
async def test_scraping_config(
    config: ScrapingConfig,
    current_user: dict = Depends(get_current_user),
    scraping_manager: ScrapingManager = Depends(get_scraping_manager)
):
    """
    Testar configuração de scraping (máximo 5 resultados)
    """
    try:
        # Limit test to 5 results
        test_config = config.copy()
        test_config.max_results = min(5, config.max_results)
        test_config.max_pages = 1
        
        # Start a test job
        job = await scraping_manager.start_scraping_job(
            user_id=current_user["user_id"],
            config=test_config
        )
        
        # Wait a bit for some results
        import asyncio
        await asyncio.sleep(2)
        
        # Get updated job status
        updated_job = scraping_manager.get_job_status(job.id)
        
        return {
            "job_id": job.id,
            "status": updated_job.status if updated_job else job.status,
            "leads_found": updated_job.leads_found if updated_job else 0,
            "message": "Teste iniciado. Use GET /jobs/{job_id} para acompanhar o progresso."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no teste: {str(e)}")

@router.get("/templates")
async def get_scraping_templates():
    """
    Obter templates de configuração para diferentes tipos de busca
    """
    templates = [
        {
            "name": "Empresas de Tecnologia",
            "description": "Buscar empresas de software e tecnologia",
            "config": {
                "search_query": "empresa software desenvolvimento",
                "industry": "Tecnologia",
                "sources": [ScrapingSource.GOOGLE_MAPS, ScrapingSource.LINKEDIN],
                "max_results": 100,
                "required_fields": ["company", "email"]
            }
        },
        {
            "name": "Restaurantes e Alimentação",
            "description": "Buscar restaurantes e empresas de alimentação",
            "config": {
                "search_query": "restaurante comida delivery",
                "industry": "Alimentação",
                "sources": [ScrapingSource.GOOGLE_MAPS],
                "max_results": 200,
                "required_fields": ["company", "phone"]
            }
        },
        {
            "name": "Serviços Profissionais",
            "description": "Advogados, contadores, consultores",
            "config": {
                "search_query": "advogado contador consultor",
                "industry": "Serviços",
                "sources": [ScrapingSource.GOOGLE_MAPS, ScrapingSource.LINKEDIN],
                "max_results": 150,
                "required_fields": ["company", "phone"]
            }
        },
        {
            "name": "E-commerce",
            "description": "Lojas online e e-commerce",
            "config": {
                "search_query": "loja online ecommerce marketplace",
                "industry": "E-commerce",
                "sources": [ScrapingSource.COMPANY_WEBSITE, ScrapingSource.GOOGLE_MAPS],
                "max_results": 100,
                "required_fields": ["company", "website"]
            }
        },
        {
            "name": "Saúde e Bem-estar",
            "description": "Clínicas, hospitais, profissionais de saúde",
            "config": {
                "search_query": "clínica hospital médico dentista",
                "industry": "Saúde",
                "sources": [ScrapingSource.GOOGLE_MAPS],
                "max_results": 200,
                "required_fields": ["company", "phone"]
            }
        }
    ]
    
    return {"templates": templates}

@router.post("/bulk-import")
async def bulk_import_leads(
    leads: List[dict],
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """
    Importar leads em massa (para integração com outras ferramentas)
    """
    try:
        from ..database.models import Lead as LeadModel
        from ..search.indexer import LeadIndexer
        
        imported_count = 0
        errors = []
        
        # Initialize indexer
        redis_client = get_redis_client()
        cache_manager = CacheManager(redis_client)
        indexer = LeadIndexer(db, cache_manager)
        
        for lead_data in leads[:100]:  # Limit to 100 per request
            try:
                # Validate required fields
                if not lead_data.get('company'):
                    errors.append(f"Lead sem nome da empresa: {lead_data}")
                    continue
                
                # Check if lead already exists
                existing = db.query(LeadModel).filter(
                    LeadModel.company.ilike(f"%{lead_data['company']}%"),
                    LeadModel.user_id == current_user["user_id"]
                ).first()
                
                if existing:
                    continue
                
                # Create lead
                lead = LeadModel(
                    user_id=current_user["user_id"],
                    company=lead_data.get('company'),
                    contact=lead_data.get('contact'),
                    email=lead_data.get('email'),
                    phone=lead_data.get('phone'),
                    website=lead_data.get('website'),
                    industry=lead_data.get('industry'),
                    location=lead_data.get('location'),
                    revenue=lead_data.get('revenue'),
                    employees=lead_data.get('employees'),
                    description=lead_data.get('description'),
                    keywords=lead_data.get('keywords', []),
                    score=lead_data.get('score', 75),
                    status="Novo",
                    priority="Média"
                )
                
                db.add(lead)
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Erro ao importar {lead_data.get('company', 'lead')}: {str(e)}")
        
        # Commit all leads
        db.commit()
        
        # Index leads
        if imported_count > 0:
            indexer.bulk_index_leads()
        
        return {
            "imported_count": imported_count,
            "error_count": len(errors),
            "errors": errors[:10]  # Return first 10 errors
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro na importação: {str(e)}")