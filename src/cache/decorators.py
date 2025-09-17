"""
Cache decorators for search results and lead data
"""
import functools
import logging
from typing import Any, Callable, Optional, Dict, List
from .manager import CacheManager

logger = logging.getLogger(__name__)

def get_cache_manager() -> CacheManager:
    """Get cache manager instance"""
    try:
        from ..database.connection import get_redis
        redis_client = get_redis()
        return CacheManager(redis_client)
    except ImportError:
        # Return disabled cache manager if database connection not available
        return CacheManager(None)

def cache_result(key_type: str, key_func: Optional[Callable] = None, ttl: Optional[int] = None):
    """
    Generic cache decorator for any function result
    
    Args:
        key_type: Type of cache key (search, lead, user_prefs, analytics)
        key_func: Function to generate cache key from function args
        ttl: Time to live in seconds
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            cache_manager = get_cache_manager()
            
            if not cache_manager.enabled:
                return func(*args, **kwargs)
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation from function name and args
                cache_key = f"{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache
            cached_result = cache_manager.get(key_type, cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {key_type}:{cache_key}")
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(key_type, cache_key, result, ttl)
            logger.debug(f"Cached result for {key_type}:{cache_key}")
            
            return result
        return wrapper
    return decorator

def cache_search_results(ttl: Optional[int] = None):
    """
    Decorator specifically for search result caching
    Expects function to return search results and take query parameters
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            cache_manager = get_cache_manager()
            
            if not cache_manager.enabled:
                return func(*args, **kwargs)
            
            # Create query data from function arguments
            query_data = {
                "function": func.__name__,
                "args": args,
                "kwargs": kwargs
            }
            
            # Try to get from cache
            cached_data = cache_manager.get_cached_search_results(query_data)
            if cached_data is not None:
                logger.debug(f"Search cache hit for query: {query_data}")
                # Track popular search
                if "text" in kwargs:
                    cache_manager.add_popular_search(kwargs["text"])
                return cached_data["results"]
            
            # Execute search function
            results = func(*args, **kwargs)
            
            # Cache results
            if isinstance(results, list):
                cache_manager.cache_search_results(query_data, results, ttl)
                logger.debug(f"Cached search results: {len(results)} items")
                
                # Track popular search
                if "text" in kwargs:
                    cache_manager.add_popular_search(kwargs["text"])
            
            return results
        return wrapper
    return decorator

def cache_lead_data(ttl: Optional[int] = None):
    """
    Decorator specifically for lead data caching
    Expects function to work with lead_id parameter
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            cache_manager = get_cache_manager()
            
            if not cache_manager.enabled:
                return func(*args, **kwargs)
            
            # Extract lead_id from arguments
            lead_id = None
            if args and len(args) > 0:
                # Assume first argument is lead_id
                lead_id = args[0]
            elif "lead_id" in kwargs:
                lead_id = kwargs["lead_id"]
            elif "id" in kwargs:
                lead_id = kwargs["id"]
            
            if lead_id is None:
                # Can't cache without lead_id, execute function normally
                return func(*args, **kwargs)
            
            # Try to get from cache
            cached_data = cache_manager.get_cached_lead_data(lead_id)
            if cached_data is not None:
                logger.debug(f"Lead cache hit for ID: {lead_id}")
                return cached_data
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            
            # Cache result if it's a dict (lead data)
            if isinstance(result, dict):
                cache_manager.cache_lead_data(lead_id, result, ttl)
                logger.debug(f"Cached lead data for ID: {lead_id}")
            
            return result
        return wrapper
    return decorator

def invalidate_cache_on_update(key_type: str, key_func: Optional[Callable] = None):
    """
    Decorator to invalidate cache when data is updated
    Use on create/update/delete functions
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Execute the function first
            result = func(*args, **kwargs)
            
            cache_manager = get_cache_manager()
            if not cache_manager.enabled:
                return result
            
            try:
                if key_type == "search":
                    # Invalidate all search caches when data changes
                    cache_manager.invalidate_search_cache()
                    logger.debug("Invalidated search cache due to data update")
                
                elif key_type == "lead":
                    # Invalidate specific lead cache
                    if key_func:
                        cache_key = key_func(*args, **kwargs)
                        cache_manager.invalidate_lead_cache(cache_key)
                    else:
                        # Try to extract lead_id
                        lead_id = None
                        if args and len(args) > 0:
                            lead_id = args[0]
                        elif "lead_id" in kwargs:
                            lead_id = kwargs["lead_id"]
                        elif "id" in kwargs:
                            lead_id = kwargs["id"]
                        
                        if lead_id:
                            cache_manager.invalidate_lead_cache(lead_id)
                            logger.debug(f"Invalidated lead cache for ID: {lead_id}")
                
                elif key_type == "user_prefs":
                    # Invalidate user preferences cache
                    if key_func:
                        cache_key = key_func(*args, **kwargs)
                        cache_manager.invalidate_user_preferences(cache_key)
                
                elif key_type == "analytics":
                    # Invalidate analytics cache
                    cache_manager.invalidate_analytics_cache()
                    logger.debug("Invalidated analytics cache due to data update")
                    
            except Exception as e:
                logger.error(f"Error invalidating cache: {e}")
            
            return result
        return wrapper
    return decorator

# Convenience decorators for common use cases
def cache_user_preferences(ttl: Optional[int] = None):
    """Cache user preferences with user email as key"""
    def key_func(*args, **kwargs):
        # Extract user email from arguments
        if "user_email" in kwargs:
            return kwargs["user_email"]
        elif args and len(args) > 0:
            return str(args[0])
        return "unknown_user"
    
    return cache_result("user_prefs", key_func, ttl)

def cache_analytics(metric_name: str, ttl: Optional[int] = None):
    """Cache analytics data with metric name as key"""
    def key_func(*args, **kwargs):
        return metric_name
    
    return cache_result("analytics", key_func, ttl)

def invalidate_search_cache(func: Callable) -> Callable:
    """Convenience decorator to invalidate search cache"""
    return invalidate_cache_on_update("search")(func)

def invalidate_lead_cache(func: Callable) -> Callable:
    """Convenience decorator to invalidate lead cache"""
    return invalidate_cache_on_update("lead")(func)