# Redis Cache Manager

A comprehensive Redis-based caching system for the Huntly MVP with TTL management, invalidation logic, and specialized decorators for search results and lead data.

## Features

- **Configurable TTL**: Different cache durations for different data types
- **Smart Invalidation**: Pattern-based and targeted cache invalidation
- **Search Optimization**: Specialized caching for search results with query hashing
- **Lead Data Caching**: Efficient caching of individual lead records
- **Popular Searches**: Track and retrieve most popular search queries
- **Health Monitoring**: Built-in health checks and monitoring
- **Graceful Degradation**: Works seamlessly when Redis is unavailable
- **Decorator Support**: Easy-to-use decorators for automatic caching

## Quick Start

### Basic Usage

```python
from src.cache import CacheManager
from src.database.connection import get_redis

# Initialize cache manager
redis_client = get_redis()
cache = CacheManager(redis_client)

# Basic operations
cache.set("search", "query_hash", results, ttl=3600)
cached_results = cache.get("search", "query_hash")
cache.delete("search", "query_hash")
```

### Using Decorators

```python
from src.cache.decorators import cache_search_results, cache_lead_data

@cache_search_results(ttl=1800)
def search_leads(text=None, filters=None):
    # Your search logic here
    return search_results

@cache_lead_data(ttl=7200)
def get_lead_by_id(lead_id):
    # Your lead fetching logic here
    return lead_data
```

## Configuration

Cache behavior is controlled through environment variables:

```bash
# TTL Settings (seconds)
CACHE_DEFAULT_TTL=3600          # 1 hour default
SEARCH_CACHE_TTL=3600           # Search results cache
LEAD_CACHE_TTL=7200             # Lead data cache (2 hours)
USER_PREFS_TTL=86400            # User preferences (24 hours)
ANALYTICS_TTL=1800              # Analytics data (30 minutes)

# Performance Settings
REDIS_MAX_CONNECTIONS=20        # Redis connection pool size
MAX_SEARCH_RESULTS=1000         # Maximum cached search results
INDEXING_BATCH_SIZE=100         # Batch size for bulk operations
```

## Cache Types and Keys

The system uses prefixed keys for different data types:

- **Search Results**: `search:{query_hash}`
- **Lead Data**: `lead:{lead_id}`
- **User Preferences**: `user_prefs:{user_email}`
- **Analytics**: `analytics:{metric_key}`
- **Suggestions**: `suggestions:{prefix}`
- **Popular Searches**: `popular_searches` (sorted set)

## API Reference

### CacheManager Class

#### Basic Operations

```python
# Set cache with TTL
cache.set(key_type, identifier, data, ttl=None)

# Get cached data
cache.get(key_type, identifier)

# Delete cache entry
cache.delete(key_type, identifier)

# Check if key exists
cache.exists(key_type, identifier)

# Get remaining TTL
cache.get_ttl(key_type, identifier)

# Invalidate by pattern
cache.invalidate_pattern("search:*")
```

#### Search-Specific Methods

```python
# Cache search results
cache.cache_search_results(query_data, results, ttl=None)

# Get cached search results
cache.get_cached_search_results(query_data)

# Invalidate all search caches
cache.invalidate_search_cache()
```

#### Lead-Specific Methods

```python
# Cache lead data
cache.cache_lead_data(lead_id, lead_data, ttl=None)

# Get cached lead data
cache.get_cached_lead_data(lead_id)

# Invalidate specific lead cache
cache.invalidate_lead_cache(lead_id)

# Invalidate all lead caches
cache.invalidate_all_lead_caches()
```

#### Popular Searches

```python
# Add to popular searches
cache.add_popular_search(query)

# Get most popular searches
cache.get_popular_searches(limit=10)
```

#### Health and Monitoring

```python
# Check cache health
health = cache.health_check()

# Clear all cache (use with caution)
cache.clear_all_cache()
```

### Decorators

#### @cache_search_results(ttl=None)

Automatically caches search function results based on parameters:

```python
@cache_search_results(ttl=1800)
def search_leads(text=None, industry=None, location=None):
    # Search logic here
    return results
```

#### @cache_lead_data(ttl=None)

Caches lead data functions that work with lead_id:

```python
@cache_lead_data(ttl=7200)
def get_lead_details(lead_id):
    # Lead fetching logic here
    return lead_data
```

#### @cache_result(key_type, key_func=None, ttl=None)

Generic caching decorator for any function:

```python
@cache_result("analytics", lambda metric: metric, ttl=1800)
def calculate_metric(metric_name):
    # Calculation logic here
    return result
```

#### @invalidate_cache_on_update(key_type, key_func=None)

Invalidates cache when data is modified:

```python
@invalidate_cache_on_update("search")
def update_lead(lead_id, updates):
    # Update logic here
    return updated_lead
```

## Error Handling

The cache manager handles errors gracefully:

- **Redis Unavailable**: Falls back to direct database queries
- **Serialization Errors**: Logs errors and continues without caching
- **Network Issues**: Automatic retry and fallback mechanisms
- **Invalid Data**: Validates data before caching

## Performance Considerations

### Cache Hit Optimization

1. **Search Results**: Cached by query hash for exact matches
2. **Lead Data**: Individual lead caching for fast lookups
3. **Batch Operations**: Efficient bulk invalidation
4. **Connection Pooling**: Optimized Redis connection management

### Memory Management

- Configurable TTL prevents memory bloat
- Pattern-based invalidation for bulk cleanup
- Automatic expiration of stale data
- Memory usage monitoring through health checks

## Testing

Run the comprehensive test suite:

```bash
# Run all cache tests
python -m pytest tests/test_cache.py -v

# Run specific test class
python -m pytest tests/test_cache.py::TestCacheManager -v

# Run with coverage
python -m pytest tests/test_cache.py --cov=src.cache
```

## Integration Examples

### Search Engine Integration

```python
from src.cache.decorators import cache_search_results, invalidate_search_cache

class SearchEngine:
    @cache_search_results(ttl=3600)
    def search(self, query, filters=None):
        # Search implementation
        return results
    
    @invalidate_search_cache
    def index_lead(self, lead_data):
        # Indexing implementation
        return indexed_lead
```

### API Endpoint Integration

```python
from fastapi import APIRouter
from src.cache import CacheManager
from src.database.connection import get_redis

router = APIRouter()
cache = CacheManager(get_redis())

@router.get("/leads/search")
async def search_leads(q: str = None):
    # Check cache first
    query_data = {"text": q}
    cached_results = cache.get_cached_search_results(query_data)
    
    if cached_results:
        return cached_results["results"]
    
    # Execute search and cache results
    results = perform_search(q)
    cache.cache_search_results(query_data, results)
    
    return results
```

## Monitoring and Debugging

### Health Check Endpoint

```python
@router.get("/health/cache")
async def cache_health():
    cache = CacheManager(get_redis())
    return cache.health_check()
```

### Cache Statistics

```python
def get_cache_stats():
    cache = CacheManager(get_redis())
    return {
        "popular_searches": cache.get_popular_searches(10),
        "health": cache.health_check(),
        "redis_info": cache.redis_client.info() if cache.enabled else None
    }
```

## Best Practices

1. **Use Appropriate TTL**: Set TTL based on data freshness requirements
2. **Cache Invalidation**: Invalidate related caches when data changes
3. **Error Handling**: Always handle cache failures gracefully
4. **Monitoring**: Monitor cache hit rates and performance
5. **Testing**: Test both cache hit and miss scenarios
6. **Memory Usage**: Monitor Redis memory usage in production

## Troubleshooting

### Common Issues

1. **Cache Not Working**: Check Redis connection and configuration
2. **High Memory Usage**: Reduce TTL or implement more aggressive invalidation
3. **Slow Performance**: Check Redis connection pool settings
4. **Stale Data**: Ensure proper cache invalidation on updates

### Debug Mode

Enable debug logging to see cache operations:

```python
import logging
logging.getLogger('src.cache').setLevel(logging.DEBUG)
```

This will log all cache hits, misses, and operations for debugging purposes.