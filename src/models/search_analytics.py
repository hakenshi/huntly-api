from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime

class SearchPerformanceMetrics(BaseModel):
    """Métricas de performance do sistema de busca"""
    total_searches_today: int
    avg_response_time_ms: int
    cache_hit_rate: float
    popular_queries: List[Dict[str, Any]]
    search_trends: Dict[str, Any]
    indexing_status: Dict[str, Any]

class SearchConversionMetrics(BaseModel):
    """Métricas de conversão de buscas"""
    search_to_contact_rate: float
    search_to_qualified_rate: float
    avg_results_per_search: float
    zero_results_rate: float
    refinement_rate: float
    conversion_by_query_type: List[Dict[str, Any]]
    top_converting_filters: List[Dict[str, Any]]

class FacetValue(BaseModel):
    """Valor de faceta com contagem"""
    value: str
    count: int

class SearchFacets(BaseModel):
    """Facetas disponíveis para filtros avançados"""
    industries: List[FacetValue]
    locations: List[FacetValue]
    company_sizes: List[FacetValue]
    revenue_ranges: List[FacetValue]

class SearchAnalytics(BaseModel):
    """Analytics completos de busca"""
    search_performance: Dict[str, Any]
    popular_searches: List[Dict[str, Any]]
    search_trends: Dict[str, Any]
    indexing_status: Dict[str, Any]
    last_updated: Optional[str] = None

class AdvancedSearchResult(BaseModel):
    """Resultado de busca avançada com analytics"""
    results: List[Any]  # RankedLead list
    total_results: int
    search_time_ms: int
    facets: Dict[str, List[FacetValue]]
    applied_filters: Dict[str, Any]
    preferences_applied: bool

class SearchSuggestion(BaseModel):
    """Sugestão de busca"""
    text: str
    type: str = "query"  # query, company, industry, location
    count: Optional[int] = None

class SearchSuggestionsResponse(BaseModel):
    """Resposta de sugestões de busca"""
    suggestions: List[str]
    categories: Optional[Dict[str, List[SearchSuggestion]]] = None