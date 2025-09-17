"""
Unit tests for Redis cache manager
"""
import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from src.cache.manager import CacheManager
from src.cache.config import CacheConfig
from src.cache.decorators import (
    cache_result, 
    cache_search_results, 
    cache_lead_data,
    invalidate_cache_on_update
)

class TestCacheConfig:
    """Test cache configuration"""
    
    def test_default_ttl_values(self):
        """Test default TTL values are set correctly"""
        assert CacheConfig.DEFAULT_TTL == 3600
        assert CacheConfig.SEARCH_RESULTS_TTL == 3600
        assert CacheConfig.LEAD_DATA_TTL == 7200
        assert CacheConfig.USER_PREFERENCES_TTL == 86400
        assert CacheConfig.ANALYTICS_TTL == 1800
    
    def test_key_prefixes(self):
        """Test key prefixes are set correctly"""
        assert CacheConfig.SEARCH_PREFIX == "search:"
        assert CacheConfig.LEAD_PREFIX == "lead:"
        assert CacheConfig.USER_PREFS_PREFIX == "user_prefs:"
        assert CacheConfig.ANALYTICS_PREFIX == "analytics:"
    
    def test_get_ttl_for_key_type(self):
        """Test TTL retrieval by key type"""
        assert CacheConfig.get_ttl_for_key_type("search") == 3600
        assert CacheConfig.get_ttl_for_key_type("lead") == 7200
        assert CacheConfig.get_ttl_for_key_type("user_prefs") == 86400
        assert CacheConfig.get_ttl_for_key_type("analytics") == 1800
        assert CacheConfig.get_ttl_for_key_type("unknown") == 3600
    
    def test_get_key_prefix(self):
        """Test key prefix retrieval by type"""
        assert CacheConfig.get_key_prefix("search") == "search:"
        assert CacheConfig.get_key_prefix("lead") == "lead:"
        assert CacheConfig.get_key_prefix("user_prefs") == "user_prefs:"
        assert CacheConfig.get_key_prefix("analytics") == "analytics:"
        assert CacheConfig.get_key_prefix("unknown") == ""

class TestCacheManager:
    """Test cache manager functionality"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.setex.return_value = True
        mock_client.get.return_value = None
        mock_client.delete.return_value = 1
        mock_client.exists.return_value = False
        mock_client.ttl.return_value = 3600
        mock_client.keys.return_value = []
        mock_client.zincrby.return_value = 1
        mock_client.zrevrange.return_value = []
        mock_client.flushdb.return_value = True
        mock_client.info.return_value = {
            "connected_clients": 1,
            "used_memory_human": "1M",
            "db0": {"keys": 10}
        }
        return mock_client
    
    @pytest.fixture
    def cache_manager(self, mock_redis):
        """Cache manager with mock Redis"""
        return CacheManager(mock_redis)
    
    @pytest.fixture
    def disabled_cache_manager(self):
        """Cache manager without Redis (disabled)"""
        return CacheManager(None)
    
    def test_initialization_with_redis(self, mock_redis):
        """Test cache manager initialization with Redis client"""
        manager = CacheManager(mock_redis)
        assert manager.redis_client == mock_redis
        assert manager.enabled is True
    
    def test_initialization_without_redis(self):
        """Test cache manager initialization without Redis client"""
        manager = CacheManager(None)
        assert manager.redis_client is None
        assert manager.enabled is False
    
    def test_generate_key(self, cache_manager):
        """Test cache key generation"""
        key = cache_manager._generate_key("search", "test_query")
        assert key == "search:test_query"
        
        key = cache_manager._generate_key("lead", "123")
        assert key == "lead:123"
    
    def test_serialize_deserialize_data(self, cache_manager):
        """Test data serialization and deserialization"""
        # Test dict
        data = {"key": "value", "number": 123}
        serialized = cache_manager._serialize_data(data)
        deserialized = cache_manager._deserialize_data(serialized)
        assert deserialized == data
        
        # Test list
        data = [1, 2, 3, "test"]
        serialized = cache_manager._serialize_data(data)
        deserialized = cache_manager._deserialize_data(serialized)
        assert deserialized == data
        
        # Test string
        data = "simple string"
        serialized = cache_manager._serialize_data(data)
        deserialized = cache_manager._deserialize_data(serialized)
        assert deserialized == data
    
    def test_hash_query(self, cache_manager):
        """Test query hashing"""
        query1 = {"text": "test", "filters": {"industry": "tech"}}
        query2 = {"filters": {"industry": "tech"}, "text": "test"}
        
        hash1 = cache_manager._hash_query(query1)
        hash2 = cache_manager._hash_query(query2)
        
        # Same content should produce same hash regardless of order
        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hash length
    
    def test_set_get_cache(self, cache_manager, mock_redis):
        """Test basic cache set and get operations"""
        # Mock Redis responses
        mock_redis.setex.return_value = True
        mock_redis.get.return_value = '{"key": "value"}'
        
        # Test set
        result = cache_manager.set("search", "test_key", {"key": "value"})
        assert result is True
        mock_redis.setex.assert_called_once()
        
        # Test get
        result = cache_manager.get("search", "test_key")
        assert result == {"key": "value"}
        mock_redis.get.assert_called_with("search:test_key")
    
    def test_cache_miss(self, cache_manager, mock_redis):
        """Test cache miss scenario"""
        mock_redis.get.return_value = None
        
        result = cache_manager.get("search", "nonexistent_key")
        assert result is None
    
    def test_delete_cache(self, cache_manager, mock_redis):
        """Test cache deletion"""
        mock_redis.delete.return_value = 1
        
        result = cache_manager.delete("search", "test_key")
        assert result is True
        mock_redis.delete.assert_called_with("search:test_key")
    
    def test_exists_cache(self, cache_manager, mock_redis):
        """Test cache existence check"""
        mock_redis.exists.return_value = 1
        
        result = cache_manager.exists("search", "test_key")
        assert result is True
        mock_redis.exists.assert_called_with("search:test_key")
    
    def test_get_ttl(self, cache_manager, mock_redis):
        """Test TTL retrieval"""
        mock_redis.ttl.return_value = 1800
        
        result = cache_manager.get_ttl("search", "test_key")
        assert result == 1800
        mock_redis.ttl.assert_called_with("search:test_key")
    
    def test_invalidate_pattern(self, cache_manager, mock_redis):
        """Test pattern-based cache invalidation"""
        mock_redis.keys.return_value = ["search:key1", "search:key2"]
        mock_redis.delete.return_value = 2
        
        result = cache_manager.invalidate_pattern("search:*")
        assert result == 2
        mock_redis.keys.assert_called_with("search:*")
        mock_redis.delete.assert_called_with("search:key1", "search:key2")
    
    def test_cache_search_results(self, cache_manager, mock_redis):
        """Test search results caching"""
        query_data = {"text": "test query", "filters": {}}
        results = [{"id": 1, "name": "Lead 1"}, {"id": 2, "name": "Lead 2"}]
        
        mock_redis.setex.return_value = True
        
        result = cache_manager.cache_search_results(query_data, results)
        assert result is True
        
        # Verify the call was made with proper structure
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 3600  # Default TTL
        
        # Verify cached data structure
        cached_data = json.loads(call_args[0][2])
        assert cached_data["query"] == query_data
        assert cached_data["results"] == results
        assert cached_data["count"] == 2
        assert "cached_at" in cached_data
    
    def test_get_cached_search_results(self, cache_manager, mock_redis):
        """Test retrieving cached search results"""
        query_data = {"text": "test query"}
        cached_data = {
            "query": query_data,
            "results": [{"id": 1}],
            "count": 1,
            "cached_at": "2023-01-01T00:00:00"
        }
        
        mock_redis.get.return_value = json.dumps(cached_data)
        
        result = cache_manager.get_cached_search_results(query_data)
        assert result == cached_data
    
    def test_cache_lead_data(self, cache_manager, mock_redis):
        """Test lead data caching"""
        lead_data = {"id": 123, "name": "Test Lead", "industry": "Tech"}
        
        mock_redis.setex.return_value = True
        
        result = cache_manager.cache_lead_data(123, lead_data)
        assert result is True
        mock_redis.setex.assert_called_with("lead:123", 7200, json.dumps(lead_data, default=str))
    
    def test_invalidate_search_cache(self, cache_manager, mock_redis):
        """Test search cache invalidation"""
        mock_redis.keys.return_value = ["search:hash1", "search:hash2"]
        mock_redis.delete.return_value = 2
        
        result = cache_manager.invalidate_search_cache()
        assert result == 2
        mock_redis.keys.assert_called_with("search:*")
    
    def test_popular_searches(self, cache_manager, mock_redis):
        """Test popular searches functionality"""
        # Test adding popular search
        mock_redis.zincrby.return_value = 1
        result = cache_manager.add_popular_search("test query")
        assert result is True
        mock_redis.zincrby.assert_called_with("popular_searches", 1, "test query")
        
        # Test getting popular searches
        mock_redis.zrevrange.return_value = ["query1", "query2", "query3"]
        result = cache_manager.get_popular_searches(3)
        assert result == ["query1", "query2", "query3"]
        mock_redis.zrevrange.assert_called_with("popular_searches", 0, 2)
    
    def test_health_check_healthy(self, cache_manager, mock_redis):
        """Test health check when Redis is healthy"""
        mock_redis.setex.return_value = True
        mock_redis.get.return_value = "test"
        mock_redis.delete.return_value = 1
        
        result = cache_manager.health_check()
        assert result["status"] == "healthy"
        assert result["redis_available"] is True
        assert "connected_clients" in result
    
    def test_health_check_disabled(self, disabled_cache_manager):
        """Test health check when cache is disabled"""
        result = disabled_cache_manager.health_check()
        assert result["status"] == "disabled"
        assert result["redis_available"] is False
    
    def test_disabled_cache_operations(self, disabled_cache_manager):
        """Test that operations return appropriate values when cache is disabled"""
        assert disabled_cache_manager.set("search", "key", "value") is False
        assert disabled_cache_manager.get("search", "key") is None
        assert disabled_cache_manager.delete("search", "key") is False
        assert disabled_cache_manager.exists("search", "key") is False
        assert disabled_cache_manager.get_ttl("search", "key") == -1
        assert disabled_cache_manager.invalidate_pattern("*") == 0

class TestCacheDecorators:
    """Test cache decorators"""
    
    @pytest.fixture
    def mock_cache_manager(self):
        """Mock cache manager"""
        manager = Mock()
        manager.enabled = True
        manager.get.return_value = None
        manager.set.return_value = True
        manager.get_cached_search_results.return_value = None
        manager.cache_search_results.return_value = True
        manager.add_popular_search.return_value = True
        manager.get_cached_lead_data.return_value = None
        manager.cache_lead_data.return_value = True
        return manager
    
    @patch('src.cache.decorators.get_cache_manager')
    def test_cache_result_decorator(self, mock_get_manager, mock_cache_manager):
        """Test generic cache result decorator"""
        mock_get_manager.return_value = mock_cache_manager
        
        @cache_result("search", ttl=1800)
        def test_function(param1, param2="default"):
            return f"result_{param1}_{param2}"
        
        # First call should execute function and cache result
        result1 = test_function("test", param2="value")
        assert result1 == "result_test_value"
        mock_cache_manager.set.assert_called_once()
        
        # Second call should return cached result
        mock_cache_manager.get.return_value = "cached_result"
        result2 = test_function("test", param2="value")
        assert result2 == "cached_result"
    
    @patch('src.cache.decorators.get_cache_manager')
    def test_cache_search_results_decorator(self, mock_get_manager, mock_cache_manager):
        """Test search results cache decorator"""
        mock_get_manager.return_value = mock_cache_manager
        
        @cache_search_results(ttl=3600)
        def search_leads(text=None, filters=None):
            return [{"id": 1, "name": "Lead 1"}]
        
        # First call should execute and cache
        result = search_leads(text="test query", filters={"industry": "tech"})
        assert len(result) == 1
        mock_cache_manager.cache_search_results.assert_called_once()
        mock_cache_manager.add_popular_search.assert_called_with("test query")
    
    @patch('src.cache.decorators.get_cache_manager')
    def test_cache_lead_data_decorator(self, mock_get_manager, mock_cache_manager):
        """Test lead data cache decorator"""
        mock_get_manager.return_value = mock_cache_manager
        
        @cache_lead_data(ttl=7200)
        def get_lead_by_id(lead_id):
            return {"id": lead_id, "name": f"Lead {lead_id}"}
        
        # First call should execute and cache
        result = get_lead_by_id(123)
        assert result["id"] == 123
        mock_cache_manager.cache_lead_data.assert_called_with(123, result, 7200)
    
    @patch('src.cache.decorators.get_cache_manager')
    def test_invalidate_cache_decorator(self, mock_get_manager, mock_cache_manager):
        """Test cache invalidation decorator"""
        mock_get_manager.return_value = mock_cache_manager
        mock_cache_manager.invalidate_search_cache.return_value = 5
        
        @invalidate_cache_on_update("search")
        def update_lead_data(lead_id, data):
            return {"updated": True, "lead_id": lead_id}
        
        result = update_lead_data(123, {"name": "Updated Lead"})
        assert result["updated"] is True
        mock_cache_manager.invalidate_search_cache.assert_called_once()
    
    @patch('src.cache.decorators.get_cache_manager')
    def test_disabled_cache_decorators(self, mock_get_manager):
        """Test decorators when cache is disabled"""
        mock_cache_manager = Mock()
        mock_cache_manager.enabled = False
        mock_get_manager.return_value = mock_cache_manager
        
        @cache_result("search")
        def test_function():
            return "result"
        
        result = test_function()
        assert result == "result"
        # Should not call any cache methods
        mock_cache_manager.get.assert_not_called()
        mock_cache_manager.set.assert_not_called()

if __name__ == "__main__":
    pytest.main([__file__])