from fastapi import APIRouter
from models.analytics import DashboardMetrics, LeadsByMonth, SourceMetrics, IndustryBreakdown, PerformanceMetrics
from typing import List

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard_metrics():
    """Métricas principais do dashboard"""
    return {
        "total_leads": 2847,
        "conversion_rate": 18.2,
        "qualified_leads": 1234,
        "average_roi": 4200
    }

@router.get("/leads-by-month", response_model=List[LeadsByMonth])
async def get_leads_by_month():
    """Evolução de leads por mês"""
    return [
        {"month": "Jan", "leads": 180, "qualified": 45},
        {"month": "Fev", "leads": 220, "qualified": 58},
        {"month": "Mar", "leads": 190, "qualified": 52},
        {"month": "Abr", "leads": 280, "qualified": 72},
        {"month": "Mai", "leads": 320, "qualified": 89},
        {"month": "Jun", "leads": 290, "qualified": 78}
    ]

@router.get("/sources", response_model=List[SourceMetrics])
async def get_lead_sources():
    """Principais fontes de leads"""
    return [
        {"source": "LinkedIn", "leads": 1247, "percentage": 43.8},
        {"source": "Google Search", "leads": 892, "percentage": 31.3},
        {"source": "Website", "leads": 456, "percentage": 16.0},
        {"source": "Referências", "leads": 252, "percentage": 8.9}
    ]

@router.get("/industries", response_model=List[IndustryBreakdown])
async def get_industry_breakdown():
    """Distribuição por setor"""
    return [
        {"industry": "Tecnologia", "count": 892},
        {"industry": "E-commerce", "count": 654},
        {"industry": "Saúde", "count": 432},
        {"industry": "Educação", "count": 321},
        {"industry": "Finanças", "count": 287},
        {"industry": "Outros", "count": 261}
    ]

@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance_metrics():
    """Métricas de performance de contato"""
    return {
        "emails_sent": 1847,
        "open_rate": 24.3,
        "click_rate": 8.7,
        "calls_made": 342
    }

@router.get("/quality-scores")
async def get_quality_scores():
    """Distribuição de scores de qualidade"""
    return {
        "high_quality": {"range": "90-100", "count": 342, "label": "Alta Prioridade"},
        "good_quality": {"range": "70-89", "count": 567, "label": "Boa Qualidade"},
        "medium_quality": {"range": "50-69", "count": 423, "label": "Média Qualidade"},
        "low_quality": {"range": "0-49", "count": 189, "label": "Baixa Prioridade"}
    }
