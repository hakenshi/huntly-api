"""
Tests for Analytics Service
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.services.analytics import AnalyticsService
from src.cache.manager import CacheManager
from src.database.models import Lead, User, Campaign


class TestAnalyticsService:
    """Test cases for AnalyticsService"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_db = Mock(spec=Session)
        self.mock_cache = Mock(spec=CacheManager)
        self.analytics_service = AnalyticsService(self.mock_db, self.mock_cache)
    
    def test_get_dashboard_metrics_with_cache_hit(self):
        """Test dashboard metrics with cache hit"""
        # Setup cache hit
        cached_data = {
            "total_leads": 100,
            "qualified_leads": 50,
            "conversion_rate": 50.0,
            "average_roi": 2500.0
        }
        self.mock_cache.get_cached_analytics_data.return_value = cached_data
        
        # Call method
        result = self.analytics_service.get_dashboard_metrics(user_id=1)
        
        # Verify cache was checked
        self.mock_cache.get_cached_analytics_data.assert_called_once_with("dashboard_metrics_1")
        
        # Verify database was not queried
        self.mock_db.query.assert_not_called()
        
        # Verify result
        assert result == cached_data
    
    def test_get_dashboard_metrics_with_cache_miss(self):
        """Test dashboard metrics with cache miss"""
        # Setup cache miss
        self.mock_cache.get_cached_analytics_data.return_value = None
        
        # Setup mock query results
        mock_query = Mock()
        mock_query.count.return_value = 100
        mock_query.filter.return_value = mock_query
        self.mock_db.query.return_value = mock_query
        
        # Call method
        result = self.analytics_service.get_dashboard_metrics(user_id=1)
        
        # Verify cache was checked
        self.mock_cache.get_cached_analytics_data.assert_called_once_with("dashboard_metrics_1")
        
        # Verify database was queried
        self.mock_db.query.assert_called()
        
        # Verify cache was updated
        self.mock_cache.cache_analytics_data.assert_called()
        
        # Verify result structure
        assert "total_leads" in result
        assert "qualified_leads" in result
        assert "conversion_rate" in result
        assert "average_roi" in result
    
    def test_get_search_performance_metrics(self):
        """Test search performance metrics calculation"""
        # Setup cache miss
        self.mock_cache.get_cached_analytics_data.return_value = None
        
        # Setup mock popular searches
        self.mock_cache.get_popular_searches.return_value = ["tech", "startup", "saas"]
        
        # Setup mock cache health
        self.mock_cache.health_check.return_value = {"status": "healthy"}
        
        # Call method
        result = self.analytics_service.get_search_performance_metrics()
        
        # Verify result structure
        assert "total_searches_today" in result
        assert "avg_response_time_ms" in result
        assert "cache_hit_rate" in result
        assert "popular_queries" in result
        assert "search_trends" in result
        assert "indexing_status" in result
        
        # Verify popular queries format
        assert isinstance(result["popular_queries"], list)
        if result["popular_queries"]:
            assert "query" in result["popular_queries"][0]
            assert "count" in result["popular_queries"][0]
    
    def test_get_leads_by_month(self):
        """Test leads by month calculation"""
        # Setup cache miss
        self.mock_cache.get_cached_analytics_data.return_value = None
        
        # Setup mock query results
        mock_monthly_data = [
            Mock(year=2024, month=1, total_leads=50, qualified_leads=25),
            Mock(year=2024, month=2, total_leads=60, qualified_leads=30),
        ]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_monthly_data
        
        self.mock_db.query.return_value = mock_query
        
        # Call method
        result = self.analytics_service.get_leads_by_month(user_id=1, months=6)
        
        # Verify result structure
        assert isinstance(result, list)
        if result:
            assert "month" in result[0]
            assert "leads" in result[0]
            assert "qualified" in result[0]
            assert "year" in result[0]
    
    def test_get_industry_breakdown(self):
        """Test industry breakdown calculation"""
        # Setup cache miss
        self.mock_cache.get_cached_analytics_data.return_value = None
        
        # Setup mock query results
        mock_industry_data = [
            Mock(industry="Technology", count=50),
            Mock(industry="Healthcare", count=30),
        ]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_industry_data
        
        self.mock_db.query.return_value = mock_query
        
        # Call method
        result = self.analytics_service.get_industry_breakdown(user_id=1, limit=10)
        
        # Verify result structure
        assert isinstance(result, list)
        if result:
            assert "industry" in result[0]
            assert "count" in result[0]
    
    def test_invalidate_analytics_cache(self):
        """Test analytics cache invalidation"""
        # Test user-specific invalidation
        result = self.analytics_service.invalidate_analytics_cache(user_id=1)
        
        # Verify cache invalidation was called
        self.mock_cache.invalidate_pattern.assert_called()
        assert result is True
        
        # Test global invalidation
        result = self.analytics_service.invalidate_analytics_cache()
        
        # Verify global cache invalidation was called
        self.mock_cache.invalidate_analytics_cache.assert_called()
        assert result is True
    
    def test_error_handling(self):
        """Test error handling in analytics service"""
        # Setup cache miss
        self.mock_cache.get_cached_analytics_data.return_value = None
        
        # Setup database error
        self.mock_db.query.side_effect = Exception("Database error")
        
        # Call method
        result = self.analytics_service.get_dashboard_metrics(user_id=1)
        
        # Verify error is handled gracefully
        assert "error" in result
        assert result["total_leads"] == 0
        assert result["qualified_leads"] == 0
        assert result["conversion_rate"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__])