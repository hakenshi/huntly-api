"""
Redis Cache Manager for Huntly MVP
Handles caching with TTL and invalidation logic
"""
import json
import hashlib
import logging
from typing import Any, Optional, List, Dict, Union
from datetime import datetime, timedelta
import redis
from .config import CacheConfig

logger = logging.getLogger(__name__)

class CacheManager:
    """Redis-based cache manager with TTL and invalidation logic"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize cache manager with Redis client"""
        self.redis_client = redis_client
        self.config = CacheConfig()
        self.enabled = redis_client is not None
        
        if not self.enabled:
            logger.warning("Cache manager initialized without Redis client - caching disabled")
    
    def _generate_key(self, key_type: str, identifier: str) -> str:
        """Generate cache key with proper prefix"""
        prefix = self.config.get_key_prefix(key_type)
        return f"{prefix}{identifier}"
    
    def _serialize_data(self, data: Any) -> str:
        """Serialize data for Redis storage"""
        if isinstance(data, (dict, list)):
            return json.dumps(data, default=str)
        return str(data)
    
    def _deserialize_data(self, data: str) -> Any:
        """Deserialize data from Redis"""
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return data
    
    def _hash_query(self, query_data: Dict[str, Any]) -> str:
        """Generate hash for query data to use as cache key"""
        query_str = json.dumps(query_data, sort_keys=True, default=str)
        return hashlib.md5(query_str.encode()).hexdigest()
    
    def set(self, key_type: str, identifier: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Set cache value with TTL"""
        if not self.enabled:
            return False
        
        try:
            cache_key = self._generate_key(key_type, identifier)
            serialized_data = self._serialize_data(data)
            
            if ttl is None:
                ttl = self.config.get_ttl_for_key_type(key_type)
            
            result = self.redis_client.setex(cache_key, ttl, serialized_data)
            logger.debug(f"Cache SET: {cache_key} (TTL: {ttl}s)")
            return result
        except Exception as e:
            logger.error(f"Cache SET error for {key_type}:{identifier}: {e}")
            return False
    
    def get(self, key_type: str, identifier: str) -> Optional[Any]:
        """Get cache value"""
        if not self.enabled:
            return None
        
        try:
            cache_key = self._generate_key(key_type, identifier)
            data = self.redis_client.get(cache_key)
            
            if data is None:
                logger.debug(f"Cache MISS: {cache_key}")
                return None
            
            logger.debug(f"Cache HIT: {cache_key}")
            return self._deserialize_data(data)
        except Exception as e:
            logger.error(f"Cache GET error for {key_type}:{identifier}: {e}")
            return None
    
    def delete(self, key_type: str, identifier: str) -> bool:
        """Delete cache value"""
        if not self.enabled:
            return False
        
        try:
            cache_key = self._generate_key(key_type, identifier)
            result = self.redis_client.delete(cache_key)
            logger.debug(f"Cache DELETE: {cache_key}")
            return bool(result)
        except Exception as e:
            logger.error(f"Cache DELETE error for {key_type}:{identifier}: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        if not self.enabled:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Cache INVALIDATE: {len(keys)} keys matching '{pattern}'")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache INVALIDATE error for pattern '{pattern}': {e}")
            return 0
    
    def exists(self, key_type: str, identifier: str) -> bool:
        """Check if cache key exists"""
        if not self.enabled:
            return False
        
        try:
            cache_key = self._generate_key(key_type, identifier)
            return bool(self.redis_client.exists(cache_key))
        except Exception as e:
            logger.error(f"Cache EXISTS error for {key_type}:{identifier}: {e}")
            return False
    
    def get_ttl(self, key_type: str, identifier: str) -> int:
        """Get remaining TTL for cache key"""
        if not self.enabled:
            return -1
        
        try:
            cache_key = self._generate_key(key_type, identifier)
            return self.redis_client.ttl(cache_key)
        except Exception as e:
            logger.error(f"Cache TTL error for {key_type}:{identifier}: {e}")
            return -1
    
    # Search-specific methods
    def cache_search_results(self, query_data: Dict[str, Any], results: List[Dict], ttl: Optional[int] = None) -> bool:
        """Cache search results with query hash as key"""
        query_hash = self._hash_query(query_data)
        cache_data = {
            "query": query_data,
            "results": results,
            "cached_at": datetime.now().isoformat(),
            "count": len(results)
        }
        return self.set("search", query_hash, cache_data, ttl)
    
    def get_cached_search_results(self, query_data: Dict[str, Any]) -> Optional[Dict]:
        """Get cached search results by query hash"""
        query_hash = self._hash_query(query_data)
        return self.get("search", query_hash)
    
    def invalidate_search_cache(self) -> int:
        """Invalidate all search result caches"""
        pattern = f"{self.config.SEARCH_PREFIX}*"
        return self.invalidate_pattern(pattern)
    
    # Lead-specific methods
    def cache_lead_data(self, lead_id: Union[int, str], lead_data: Dict, ttl: Optional[int] = None) -> bool:
        """Cache individual lead data"""
        return self.set("lead", str(lead_id), lead_data, ttl)
    
    def get_cached_lead_data(self, lead_id: Union[int, str]) -> Optional[Dict]:
        """Get cached lead data"""
        return self.get("lead", str(lead_id))
    
    def invalidate_lead_cache(self, lead_id: Union[int, str]) -> bool:
        """Invalidate specific lead cache"""
        return self.delete("lead", str(lead_id))
    
    def invalidate_all_lead_caches(self) -> int:
        """Invalidate all lead caches"""
        pattern = f"{self.config.LEAD_PREFIX}*"
        return self.invalidate_pattern(pattern)
    
    # User preferences methods
    def cache_user_preferences(self, user_email: str, preferences: Dict, ttl: Optional[int] = None) -> bool:
        """Cache user preferences"""
        return self.set("user_prefs", user_email, preferences, ttl)
    
    def get_cached_user_preferences(self, user_email: str) -> Optional[Dict]:
        """Get cached user preferences"""
        return self.get("user_prefs", user_email)
    
    def invalidate_user_preferences(self, user_email: str) -> bool:
        """Invalidate user preferences cache"""
        return self.delete("user_prefs", user_email)
    
    # Analytics methods
    def cache_analytics_data(self, metric_key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Cache analytics data"""
        return self.set("analytics", metric_key, data, ttl)
    
    def get_cached_analytics_data(self, metric_key: str) -> Optional[Any]:
        """Get cached analytics data"""
        return self.get("analytics", metric_key)
    
    def invalidate_analytics_cache(self) -> int:
        """Invalidate all analytics caches"""
        pattern = f"{self.config.ANALYTICS_PREFIX}*"
        return self.invalidate_pattern(pattern)
    
    # Popular searches and suggestions
    def add_popular_search(self, query: str) -> bool:
        """Add to popular searches with score increment"""
        if not self.enabled:
            return False
        
        try:
            self.redis_client.zincrby(self.config.POPULAR_SEARCHES_KEY, 1, query)
            return True
        except Exception as e:
            logger.error(f"Error adding popular search '{query}': {e}")
            return False
    
    def get_popular_searches(self, limit: int = 10) -> List[str]:
        """Get most popular searches"""
        if not self.enabled:
            return []
        
        try:
            return self.redis_client.zrevrange(self.config.POPULAR_SEARCHES_KEY, 0, limit - 1)
        except Exception as e:
            logger.error(f"Error getting popular searches: {e}")
            return []
    
    def cache_suggestions(self, prefix: str, suggestions: List[str], ttl: Optional[int] = None) -> bool:
        """Cache autocomplete suggestions for a prefix"""
        return self.set("suggestions", prefix, suggestions, ttl)
    
    def get_cached_suggestions(self, prefix: str) -> Optional[List[str]]:
        """Get cached autocomplete suggestions"""
        return self.get("suggestions", prefix)
    
    # Indexing-specific methods for lead search
    def set_inverted_index(self, term: str, lead_ids: List[int], ttl: Optional[int] = None) -> bool:
        """Set inverted index for a search term"""
        return self.set("index", term.lower(), lead_ids, ttl)
    
    def get_inverted_index(self, term: str) -> Optional[List[int]]:
        """Get lead IDs for a search term from inverted index"""
        return self.get("index", term.lower())
    
    def add_to_inverted_index(self, term: str, lead_id: int) -> bool:
        """Add lead ID to inverted index for a term"""
        if not self.enabled:
            return False
        
        try:
            key = self._generate_key("index", term.lower())
            self.redis_client.sadd(key, lead_id)
            return True
        except Exception as e:
            logger.error(f"Error adding to inverted index {term}:{lead_id}: {e}")
            return False
    
    def remove_from_inverted_index(self, term: str, lead_id: int) -> bool:
        """Remove lead ID from inverted index for a term"""
        if not self.enabled:
            return False
        
        try:
            key = self._generate_key("index", term.lower())
            self.redis_client.srem(key, lead_id)
            return True
        except Exception as e:
            logger.error(f"Error removing from inverted index {term}:{lead_id}: {e}")
            return False
    
    def get_index_intersection(self, terms: List[str]) -> List[int]:
        """Get intersection of lead IDs for multiple terms"""
        if not self.enabled or not terms:
            return []
        
        try:
            keys = [self._generate_key("index", term.lower()) for term in terms]
            # Use Redis SINTER to get intersection
            result = self.redis_client.sinter(*keys)
            return [int(lead_id) for lead_id in result]
        except Exception as e:
            logger.error(f"Error getting index intersection for terms {terms}: {e}")
            return []
    
    # Health and monitoring
    def health_check(self) -> Dict[str, Any]:
        """Check cache health and return status"""
        if not self.enabled:
            return {"status": "disabled", "redis_available": False}
        
        try:
            # Test basic operations
            test_key = "health_check_test"
            self.redis_client.setex(test_key, 10, "test")
            result = self.redis_client.get(test_key)
            self.redis_client.delete(test_key)
            
            # Get Redis info
            info = self.redis_client.info()
            
            return {
                "status": "healthy" if result == "test" else "error",
                "redis_available": True,
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "keyspace": info.get("db0", {})
            }
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {
                "status": "error",
                "redis_available": False,
                "error": str(e)
            }
    
    def clear_all_cache(self) -> bool:
        """Clear all cache data (use with caution)"""
        if not self.enabled:
            return False
        
        try:
            self.redis_client.flushdb()
            logger.warning("All cache data cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    # Additional methods for enhanced search functionality
    def cache_data(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Generic cache data method"""
        if not self.enabled:
            return False
        
        try:
            serialized_data = self._serialize_data(data)
            if ttl is None:
                ttl = 3600  # Default 1 hour
            
            result = self.redis_client.setex(key, ttl, serialized_data)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return result
        except Exception as e:
            logger.error(f"Cache SET error for {key}: {e}")
            return False
    
    def get_cached_data(self, key: str) -> Optional[Any]:
        """Generic get cached data method"""
        if not self.enabled:
            return None
        
        try:
            data = self.redis_client.get(key)
            if data is None:
                logger.debug(f"Cache MISS: {key}")
                return None
            
            logger.debug(f"Cache HIT: {key}")
            return self._deserialize_data(data)
        except Exception as e:
            logger.error(f"Cache GET error for {key}: {e}")
            return None
    
    def search_leads_by_tokens(self, tokens: List[str], limit: int = 100) -> List[int]:
        """Search leads using Redis inverted index with multiple tokens"""
        if not self.enabled or not tokens:
            return []
        
        try:
            # Get intersection of all tokens
            if len(tokens) == 1:
                key = self._generate_key("index", tokens[0].lower())
                result = self.redis_client.smembers(key)
                return [int(lead_id) for lead_id in result][:limit]
            else:
                keys = [self._generate_key("index", token.lower()) for token in tokens]
                result = self.redis_client.sinter(*keys)
                return [int(lead_id) for lead_id in result][:limit]
        except Exception as e:
            logger.error(f"Error searching leads by tokens {tokens}: {e}")
            return []
    
    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Get cache statistics for analytics"""
        if not self.enabled:
            return None
        
        try:
            info = self.redis_client.info()
            stats = info.get("stats", {})
            
            return {
                "hits": stats.get("keyspace_hits", 0),
                "misses": stats.get("keyspace_misses", 0),
                "total_commands": stats.get("total_commands_processed", 0),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "keys_count": self._get_total_keys_count()
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return None
    
    def _get_total_keys_count(self) -> int:
        """Get total number of keys in Redis"""
        try:
            info = self.redis_client.info("keyspace")
            db_info = info.get("db0", {})
            if isinstance(db_info, dict):
                return db_info.get("keys", 0)
            elif isinstance(db_info, str):
                # Parse string format: "keys=123,expires=45,avg_ttl=678"
                for part in db_info.split(","):
                    if part.startswith("keys="):
                        return int(part.split("=")[1])
            return 0
        except Exception as e:
            logger.error(f"Error getting keys count: {e}")
            return 0
    
    def increment_counter(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> int:
        """Increment a counter in Redis"""
        if not self.enabled:
            return 0
        
        try:
            result = self.redis_client.incr(key, amount)
            if ttl and result == amount:  # First time setting the key
                self.redis_client.expire(key, ttl)
            return result
        except Exception as e:
            logger.error(f"Error incrementing counter {key}: {e}")
            return 0
    
    def get_counter(self, key: str) -> int:
        """Get counter value from Redis"""
        if not self.enabled:
            return 0
        
        try:
            result = self.redis_client.get(key)
            return int(result) if result else 0
        except Exception as e:
            logger.error(f"Error getting counter {key}: {e}")
            return 0
    
    def set_hash_field(self, hash_key: str, field: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a field in a Redis hash"""
        if not self.enabled:
            return False
        
        try:
            serialized_value = self._serialize_data(value)
            result = self.redis_client.hset(hash_key, field, serialized_value)
            if ttl:
                self.redis_client.expire(hash_key, ttl)
            return bool(result)
        except Exception as e:
            logger.error(f"Error setting hash field {hash_key}:{field}: {e}")
            return False
    
    def get_hash_field(self, hash_key: str, field: str) -> Optional[Any]:
        """Get a field from a Redis hash"""
        if not self.enabled:
            return None
        
        try:
            result = self.redis_client.hget(hash_key, field)
            return self._deserialize_data(result) if result else None
        except Exception as e:
            logger.error(f"Error getting hash field {hash_key}:{field}: {e}")
            return None
    
    def get_all_hash_fields(self, hash_key: str) -> Dict[str, Any]:
        """Get all fields from a Redis hash"""
        if not self.enabled:
            return {}
        
        try:
            result = self.redis_client.hgetall(hash_key)
            return {
                field.decode() if isinstance(field, bytes) else field: 
                self._deserialize_data(value.decode() if isinstance(value, bytes) else value)
                for field, value in result.items()
            }
        except Exception as e:
            logger.error(f"Error getting all hash fields {hash_key}: {e}")
            return {}