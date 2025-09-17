from fastapi import APIRouter
from ..models.analytics import DashboardMetrics, LeadsByMonth, SourceMetrics, IndustryBreakdown, PerformanceMetrics
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

@router.get("/search-performance")
async def get_search_performance():
    """Métricas de performance do sistema de busca"""
    return {
        "total_searches_today": 127,
        "avg_response_time_ms": 145,
        "cache_hit_rate": 78.5,
        "popular_queries": [
            {"query": "tecnologia são paulo", "count": 23},
            {"query": "ecommerce", "count": 18},
            {"query": "startup fintech", "count": 15},
            {"query": "saúde digital", "count": 12},
            {"query": "educação online", "count": 9}
        ],
        "search_trends": {
            "hourly_searches": [
                {"hour": "08:00", "searches": 12},
                {"hour": "09:00", "searches": 18},
                {"hour": "10:00", "searches": 25},
                {"hour": "11:00", "searches": 22},
                {"hour": "12:00", "searches": 15},
                {"hour": "13:00", "searches": 8},
                {"hour": "14:00", "searches": 19},
                {"hour": "15:00", "searches": 24},
                {"hour": "16:00", "searches": 21},
                {"hour": "17:00", "searches": 16}
            ]
        },
        "indexing_status": {
            "total_leads": 2847,
            "indexed_leads": 2834,
            "indexing_coverage": 99.5,
            "last_index_update": "2024-01-15T14:30:00Z"
        }
    }

@router.get("/search-conversion")
async def get_search_conversion_metrics():
    """Métricas de conversão de buscas"""
    return {
        "search_to_contact_rate": 24.3,
        "search_to_qualified_rate": 8.7,
        "avg_results_per_search": 12.5,
        "zero_results_rate": 3.2,
        "refinement_rate": 18.9,
        "conversion_by_query_type": [
            {"type": "Company Name", "searches": 45, "conversions": 18, "rate": 40.0},
            {"type": "Industry + Location", "searches": 38, "conversions": 12, "rate": 31.6},
            {"type": "Technology Keywords", "searches": 29, "conversions": 6, "rate": 20.7},
            {"type": "General Terms", "searches": 15, "conversions": 2, "rate": 13.3}
        ],
        "top_converting_filters": [
            {"filter": "industry:Tecnologia", "usage": 156, "conversion_rate": 28.2},
            {"filter": "location:São Paulo", "usage": 134, "conversion_rate": 25.4},
            {"filter": "size:11-50", "usage": 89, "conversion_rate": 22.5},
            {"filter": "revenue:1M-10M", "usage": 67, "conversion_rate": 19.4}
        ]
    }