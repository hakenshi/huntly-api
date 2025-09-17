"""
Tests for enhanced search API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from src.models.search import SearchQuery, SearchFilters
from src.models.lead import RankedLead

client = TestClient(app)

class TestEnhancedSearchAPI:
    """Test enhanced search API endpoints"""
    
    @patch('src.routes.leads.get_current_user_id')
    @patch('src.routes.leads.get_db')
    @patch('src.routes.leads.get_redis')
    def test_search_facets_endpoint(self, mock_redis, mock_db, mock_user_id):
        """Test search facets endpoint"""
        # Mock dependencies
        mock_user_id.return_value = 1
        mock_db_session = Mock()
        mock_db.return_value = mock_db_session
        mock_redis.return_value = Mock()
        
        # Mock database query results
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [
            ("Tecnologia", 25),
            ("E-commerce", 18),
            ("Saúde", 12)
        ]
        
        # Test request
        response = client.get("/leads/search/facets?q=tecnologia")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "industries" in data
        assert "locations" in data
        assert "company_sizes" in data
        assert "revenue_ranges" in data
        
        # Verify facet structure
        if data["industries"]:
            facet = data["industries"][0]
            assert "value" in facet
            assert "count" in facet
    
    @patch('src.routes.leads.get_current_user_id')
    @patch('src.routes.leads.get_db')
    @patch('src.routes.leads.get_redis')
    def test_search_analytics_endpoint(self, mock_redis, mock_db, mock_user_id):
        """Test search analytics endpoint"""
        # Mock dependencies
        mock_user_id.return_value = 1
        mock_db_session = Mock()
        mock_db.return_value = mock_db_session
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        # Mock database queries
        mock_db_session.query.return_value.filter.return_value.scalar.return_value = 100
        
        # Mock search engine
        with patch('src.routes.leads.SearchEngine') as mock_search_engine:
            mock_engine = Mock()
            mock_search_engine.return_value = mock_engine
            mock_engine.get_search_stats.return_value = {
                "indexing_status": {"total_leads": 100, "indexed_leads": 95},
                "cache_health": {"hit_rate": 0.75},
                "last_updated": "2024-01-15T10:00:00Z"
            }
            
            # Mock cache manager
            with patch('src.routes.leads.CacheManager') as mock_cache_manager:
                mock_cache = Mock()
                mock_cache_manager.return_value = mock_cache
                mock_cache.get_popular_searches.return_value = ["tech", "startup", "saas"]
                
                response = client.get("/leads/search/analytics")
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify response structure
                assert "search_performance" in data
                assert "popular_searches" in data
                assert "search_trends" in data
                assert "indexing_status" in data
                
                # Verify search performance metrics
                perf = data["search_performance"]
                assert "total_leads" in perf
                assert "indexed_leads" in perf
                assert "search_coverage_percent" in perf
                assert "avg_response_time_ms" in perf
    
    @patch('src.routes.leads.get_current_user_id')
    @patch('src.routes.leads.get_db')
    @patch('src.routes.leads.get_redis')
    def test_advanced_search_endpoint(self, mock_redis, mock_db, mock_user_id):
        """Test advanced search endpoint"""
        # Mock dependencies
        mock_user_id.return_value = 1
        mock_db_session = Mock()
        mock_db.return_value = mock_db_session
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        # Mock search engine and results
        with patch('src.routes.leads.SearchEngine') as mock_search_engine:
            mock_engine = Mock()
            mock_search_engine.return_value = mock_engine
            
            # Mock search result
            mock_indexed_lead = Mock()
            mock_indexed_lead.id = 1
            mock_indexed_lead.company = "Test Company"
            mock_indexed_lead.contact = "John Doe"
            mock_indexed_lead.email = "john@test.com"
            mock_indexed_lead.phone = "+5511999999999"
            mock_indexed_lead.website = "https://test.com"
            mock_indexed_lead.industry = "Tecnologia"
            mock_indexed_lead.location = "São Paulo"
            mock_indexed_lead.revenue = "1M-10M"
            mock_indexed_lead.employees = "11-50"
            mock_indexed_lead.description = "Test description"
            mock_indexed_lead.keywords = ["tech", "startup"]
            mock_indexed_lead.indexed_at = datetime.now()
            
            mock_search_result = Mock()
            mock_search_result.lead = mock_indexed_lead
            mock_search_result.relevance_score = 0.85
            mock_search_result.match_reasons = ["Industry match", "Location match"]
            
            mock_engine.search_leads.return_value = [mock_search_result]
            
            # Mock preferences service
            with patch('src.routes.leads.PreferencesService') as mock_prefs_service:
                mock_prefs = Mock()
                mock_prefs_service.return_value = mock_prefs
                mock_prefs.get_user_preferences.return_value = None
                
                # Test request
                search_data = {
                    "text": "tecnologia startup",
                    "filters": {
                        "industry": "Tecnologia",
                        "location": "São Paulo"
                    },
                    "limit": 20,
                    "offset": 0,
                    "use_preferences": True
                }
                
                facet_filters = {
                    "industries": ["Tecnologia"],
                    "locations": ["São Paulo"]
                }
                
                response = client.post(
                    "/leads/search/advanced",
                    json=search_data,
                    params={"facet_filters": facet_filters}
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify response structure
                assert "results" in data
                assert "total_results" in data
                assert "search_time_ms" in data
                assert "facets" in data
                assert "applied_filters" in data
                assert "preferences_applied" in data
                
                # Verify results structure
                if data["results"]:
                    result = data["results"][0]
                    assert "id" in result
                    assert "company" in result
                    assert "relevance_score" in result
                    assert "match_reasons" in result
    
    def test_search_facets_without_query(self):
        """Test search facets endpoint without query parameter"""
        with patch('src.routes.leads.get_current_user_id') as mock_user_id, \
             patch('src.routes.leads.get_db') as mock_db, \
             patch('src.routes.leads.get_redis') as mock_redis:
            
            mock_user_id.return_value = 1
            mock_db_session = Mock()
            mock_db.return_value = mock_db_session
            mock_redis.return_value = Mock()
            
            # Mock empty results
            mock_query = Mock()
            mock_db_session.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.group_by.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all.return_value = []
            
            response = client.get("/leads/search/facets")
            
            assert response.status_code == 200
            data = response.json()
            
            # Should return empty facets
            assert data["industries"] == []
            assert data["locations"] == []
            assert data["company_sizes"] == []
            assert data["revenue_ranges"] == []
    
    def test_search_analytics_error_handling(self):
        """Test search analytics endpoint error handling"""
        with patch('src.routes.leads.get_current_user_id') as mock_user_id, \
             patch('src.routes.leads.get_db') as mock_db, \
             patch('src.routes.leads.get_redis') as mock_redis:
            
            mock_user_id.return_value = 1
            mock_db.return_value = Mock()
            mock_redis.return_value = Mock()
            
            # Mock search engine to raise exception
            with patch('src.routes.leads.SearchEngine') as mock_search_engine:
                mock_search_engine.side_effect = Exception("Database connection error")
                
                response = client.get("/leads/search/analytics")
                
                assert response.status_code == 500
                assert "Erro ao obter analytics" in response.json()["detail"]
    
    @patch('src.routes.leads.get_current_user_id')
    @patch('src.routes.leads.get_db')
    @patch('src.routes.leads.get_redis')
    def test_search_suggestions_with_categories(self, mock_redis, mock_db, mock_user_id):
        """Test search suggestions endpoint"""
        # Mock dependencies
        mock_user_id.return_value = 1
        mock_db_session = Mock()
        mock_db.return_value = mock_db_session
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        
        # Mock search engine
        with patch('src.routes.leads.SearchEngine') as mock_search_engine:
            mock_engine = Mock()
            mock_search_engine.return_value = mock_engine
            mock_engine.get_search_suggestions.return_value = [
                "tecnologia",
                "tecnologia startup",
                "tecnologia são paulo"
            ]
            
            # Mock cache manager
            with patch('src.routes.leads.CacheManager') as mock_cache_manager:
                mock_cache = Mock()
                mock_cache_manager.return_value = mock_cache
                
                response = client.get("/leads/search/suggestions?q=tech&limit=5")
                
                assert response.status_code == 200
                data = response.json()
                
                assert "suggestions" in data
                assert isinstance(data["suggestions"], list)
                assert len(data["suggestions"]) <= 5

if __name__ == "__main__":
    pytest.main([__file__])